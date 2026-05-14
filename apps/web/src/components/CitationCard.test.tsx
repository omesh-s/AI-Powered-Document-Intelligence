import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CitationCard } from "@/components/CitationCard";

describe("CitationCard", () => {
  it("renders document name and excerpt", () => {
    render(
      <CitationCard
        c={{
          document_id: "d1",
          document_name: "Lease.pdf",
          document_version_id: "v1",
          page_number: 2,
          chunk_id: "c1",
          excerpt: "Rent shall be due on the first day.",
          score: 0.91,
        }}
      />,
    );
    expect(screen.getByText("Lease.pdf")).toBeInTheDocument();
    expect(screen.getByText(/Rent shall be due/)).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });
});
