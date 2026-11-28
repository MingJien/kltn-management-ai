"""Export faculty source previews using desktop Word and Excel on Windows."""
from __future__ import annotations

from argparse import ArgumentParser
from contextlib import contextmanager, suppress
from pathlib import Path
from tempfile import NamedTemporaryFile

from backend.api.dependencies import load_local_env


@contextmanager
def office_application(program: str):
    from pywintypes import com_error
    from win32com.client import DispatchEx, gencache

    app = DispatchEx(f"{program}.Application")
    restore_update_links = False
    try:
        if program == "Word":
            app = gencache.EnsureDispatch(app)
        app.Visible = False
        app.AutomationSecurity = 3  # msoAutomationSecurityForceDisable
        if program == "Word":
            app.DisplayAlerts = 0  # wdAlertsNone
            restore_update_links = bool(app.Options.UpdateLinksAtOpen)
            if restore_update_links:
                app.Options.UpdateLinksAtOpen = False
        else:
            app.DisplayAlerts = False
            app.EnableEvents = False
        yield app
    finally:
        if restore_update_links:
            with suppress(com_error):
                app.Options.UpdateLinksAtOpen = True
        with suppress(com_error):
            if program == "Word":
                app.Quit(SaveChanges=0)  # wdDoNotSaveChanges
            else:
                app.Quit()


def export_pdf(app, source: Path, output: Path) -> None:
    if source.suffix.lower() == ".docx":
        document = app.Documents.Open(str(source), ConfirmConversions=False, ReadOnly=True,
                                      AddToRecentFiles=False, Visible=False)
        try:
            # Retain saved cross-reference results when PDF export repaginates.
            for field in document.Fields:
                if field.Type in {3, 13, 37, 73}:  # REF, TOC, PAGEREF, TOA
                    field.Locked = True
            document.ExportAsFixedFormat(str(output), 17, IncludeDocProps=False)  # wdExportFormatPDF
        finally:
            document.Close(SaveChanges=0)
    else:
        workbook = app.Workbooks.Open(str(source), UpdateLinks=0, ReadOnly=True,
                                      IgnoreReadOnlyRecommended=True, AddToMru=False)
        try:
            workbook.ExportAsFixedFormat(0, str(output), IncludeDocProperties=False, IgnorePrintAreas=False)
        finally:
            workbook.Close(SaveChanges=False)


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Regenerate previews for unchanged sources too.")
    args = parser.parse_args()
    load_local_env()
    from backend.services.form_templates import PREVIEW_DIR, list_sources, source_hash, source_path

    sources = [source_path(item["id"]) for item in list_sources()]
    if not sources:
        print("No faculty source files were found.")
        return 1
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    pending = []
    for source in sources:
        digest = source_hash(source)
        destination = PREVIEW_DIR / f"{digest}.pdf"
        if args.refresh or not destination.is_file():
            pending.append((source, digest, destination))

    failures = 0
    for source, digest, destination in pending:
        program = "Word" if source.suffix.lower() == ".docx" else "Excel"
        with NamedTemporaryFile(suffix=".pdf", dir=PREVIEW_DIR, delete=False) as temp:
            output = Path(temp.name)
        try:
            with office_application(program) as app:
                export_pdf(app, source, output)
            with output.open("rb") as stream:
                if stream.read(5) != b"%PDF-":
                    raise ValueError("Office did not produce a PDF.")
            if source_hash(source) != digest:
                raise ValueError("The source changed during export. Run the exporter again.")
            output.replace(destination)
            print(f"OK {source.name}", flush=True)
        except Exception as exc:
            failures += 1
            print(f"FAIL {source.name}: {exc}", flush=True)
        finally:
            output.unlink(missing_ok=True)
    print(f"Previews ready: {len(sources) - failures}/{len(sources)}.", flush=True)
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
