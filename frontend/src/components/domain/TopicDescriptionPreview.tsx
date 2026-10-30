type TopicDescriptionPreviewProps = {
  description: string | null;
};

/** A compact topic-card description. The detail dialog always shows the full text. */
export default function TopicDescriptionPreview({description}: TopicDescriptionPreviewProps) {
  const text = description?.trim() || "Chưa có mô tả đề tài.";
  return <p className="topic-card__description" title={text}>{text}</p>;
}
