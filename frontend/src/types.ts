export interface User { id: number; username: string }
export interface Space { id: number; name: string; owner_id: number | null; is_public: boolean; picture_count: number; used_bytes: number }
export interface Picture { id: string; title: string; description: string; space_id: number; space_name: string; is_public: boolean; width: number; height: number; byte_size: number; created_at: number; tags: string[]; can_edit: boolean }
export interface Tag { name: string; count: number }
export interface PicturePage { items: Picture[]; total: number; page: number; size: number }
