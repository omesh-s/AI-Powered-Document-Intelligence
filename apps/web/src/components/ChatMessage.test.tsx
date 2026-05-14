import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ChatMessage } from "@/components/ChatMessage";

describe("ChatMessage", () => {
  it("shows insufficient styling for assistant", () => {
    const { container } = render(
      <ChatMessage
        role="assistant"
        content="There is insufficient evidence in the indexed document context."
        answerability="insufficient_evidence"
        citations={[]}
      />,
    );
    expect(screen.getAllByText(/Insufficient evidence/i).length).toBeGreaterThanOrEqual(1);
    expect(container.querySelector(".border-amber-300")).toBeTruthy();
  });

  it("renders citation cards for grounded answers", () => {
    render(
      <ChatMessage
        role="assistant"
        content="Based on the contract, payment is net 30."
        answerability="grounded"
        citations={[
          {
            document_id: "d",
            document_name: "Contract.pdf",
            document_version_id: "v",
            page_number: 1,
            chunk_id: "c",
            excerpt: "Payment terms net thirty days.",
            score: 0.88,
          },
        ]}
      />,
    );
    expect(screen.getByText("Contract.pdf")).toBeInTheDocument();
    expect(screen.getByText(/Payment terms/)).toBeInTheDocument();
  });
});
