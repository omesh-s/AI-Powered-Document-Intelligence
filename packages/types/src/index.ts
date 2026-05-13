import { z } from "zod";

/** Mirrors backend enum ordering for stable wire contracts. */
export const DocumentLifecycleStatusSchema = z.enum([
  "uploaded",
  "queued",
  "parsing",
  "ocr_in_progress",
  "chunking",
  "embedding",
  "indexed",
  "failed",
]);
export type DocumentLifecycleStatus = z.infer<typeof DocumentLifecycleStatusSchema>;

export const ApiErrorEnvelopeSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    details: z.unknown().nullable(),
    requestId: z.string(),
  }),
});
export type ApiErrorEnvelope = z.infer<typeof ApiErrorEnvelopeSchema>;

export const HealthResponseSchema = z.object({
  status: z.literal("ok"),
  version: z.string(),
});
export type HealthResponse = z.infer<typeof HealthResponseSchema>;
