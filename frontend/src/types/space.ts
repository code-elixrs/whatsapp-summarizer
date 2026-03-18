export interface SpaceItemCounts {
  calls: number;
  chats: number;
  statuses: number;
  media: number;
}

export interface Space {
  id: string;
  name: string;
  description: string | null;
  color: string;
  created_at: string;
  updated_at: string;
  item_counts: SpaceItemCounts;
}

export interface SpaceListResponse {
  spaces: Space[];
  total: number;
}

export interface SpaceCreate {
  name: string;
  description?: string;
  color?: string;
}

export interface SpaceUpdate {
  name?: string;
  description?: string | null;
  color?: string;
}
