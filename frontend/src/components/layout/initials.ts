/**
 * 2-letter avatar initials: first character of the first two words.
 * "Sinh viên giả lập 3" -> "SV", "Nguyễn Văn A" -> "NA", single word -> first char.
 */
export function initialsOf(name: string): string {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length >= 2) return (words[0].charAt(0) + words[1].charAt(0)).toUpperCase();
  return (words[0]?.charAt(0) ?? "?").toUpperCase();
}
