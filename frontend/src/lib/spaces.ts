import type { Space, SpaceCreate, SpaceListResponse, SpaceUpdate } from "../types/space";
import { apiFetch } from "./api";

export function listSpaces(search?: string): Promise<SpaceListResponse> {
  const params = search ? `?search=${encodeURIComponent(search)}` : "";
  return apiFetch<SpaceListResponse>(`/spaces${params}`);
}

export function getSpace(id: string): Promise<Space> {
  return apiFetch<Space>(`/spaces/${id}`);
}

export function createSpace(data: SpaceCreate): Promise<Space> {
  return apiFetch<Space>("/spaces", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateSpace(id: string, data: SpaceUpdate): Promise<Space> {
  return apiFetch<Space>(`/spaces/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function deleteSpace(id: string): Promise<void> {
  return apiFetch<void>(`/spaces/${id}`, { method: "DELETE" });
}
