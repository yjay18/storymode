/**
 * Typed API client errors (UI-02).
 */

export class ApiClientError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiClientError";
  }
}

export class ApiHttpError extends ApiClientError {
  readonly status: number;
  readonly code: string;
  readonly details?: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = "ApiHttpError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

export class ApiNetworkError extends ApiClientError {
  constructor(message: string, readonly cause?: unknown) {
    super(message);
    this.name = "ApiNetworkError";
  }
}

export class ApiTimeoutError extends ApiClientError {
  constructor(message: string = "Request timed out") {
    super(message);
    this.name = "ApiTimeoutError";
  }
}

export class ApiConflictError extends ApiHttpError {
  constructor(message: string, details?: unknown) {
    super(409, "conflict", message, details);
    this.name = "ApiConflictError";
  }
}

export class ApiValidationError extends ApiHttpError {
  constructor(message: string, details?: unknown) {
    super(422, "validation_error", message, details);
    this.name = "ApiValidationError";
  }
}

export class ApiNotFoundError extends ApiHttpError {
  constructor(message: string, details?: unknown) {
    super(404, "not_found", message, details);
    this.name = "ApiNotFoundError";
  }
}
