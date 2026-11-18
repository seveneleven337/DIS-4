import {
  RecordCreate,
  RecordResponse,
  RecordSource,
  RecordUpdate,
} from "@/types/record";

const API_URL = "/api/records";

interface ApiError {
  detail?: string | Array<{ msg?: string; loc?: (string | number)[] }>;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error: ApiError = await response.json().catch(() => ({}));

    const message = Array.isArray(error.detail)
      ? error.detail.map((item) => item.msg ?? "Validation error").join("; ")
      : error.detail ?? `Request failed (${response.status})`;

    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export async function getRecords(
  source: RecordSource = "ALL",
  search = "",
): Promise<RecordResponse[]> {
  const params = new URLSearchParams({
    source,
    limit: "500",
    offset: "0",
  });

  const response = await fetch(`${API_URL}?${params.toString()}`, {
    method: "GET",
    cache: "no-store",
  });

  const records = await handleResponse<RecordResponse[]>(response);
  const normalizedSearch = search.trim().toLocaleLowerCase();

  if (!normalizedSearch) {
    return records;
  }

  return records.filter((record) =>
    JSON.stringify(record).toLocaleLowerCase().includes(normalizedSearch),
  );
}

export async function getRecord(
  orderId: string,
): Promise<RecordResponse> {
  const response = await fetch(
    `${API_URL}/${encodeURIComponent(orderId)}`,
    {
      method: "GET",
      cache: "no-store",
    },
  );

  return handleResponse<RecordResponse>(response);
}

export async function createRecord(
  record: RecordCreate,
): Promise<RecordResponse> {
  const response = await fetch(API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(record),
    cache: "no-store",
  });

  return handleResponse<RecordResponse>(response);
}

export async function updateRecord(
  orderId: string,
  record: RecordUpdate,
): Promise<RecordResponse> {
  const response = await fetch(
    `${API_URL}/${encodeURIComponent(orderId)}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(record),
    },
  );

  return handleResponse<RecordResponse>(response);
}

export async function deleteRecord(
  orderId: string,
  expectedVersion: number,
): Promise<void> {
  const response = await fetch(
    `${API_URL}/${encodeURIComponent(orderId)}?expected_version=${expectedVersion}`,
    {
      method: "DELETE",
    },
  );

  return handleResponse<void>(response);
}
