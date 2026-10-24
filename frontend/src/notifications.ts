export type Notice = {
  id: string;
  message: string;
  created_at: string;
  read_at: string | null;
  url: string;
};

export type NoticeSummary = {unread_count: number; items: Notice[]};
