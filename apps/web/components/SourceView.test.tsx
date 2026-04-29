import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { SourceView } from "./SourceView";
import type { ProjectFile } from "@/lib/types";

vi.mock("shiki", () => ({
  codeToHtml: async (code: string) => `<pre>${code}</pre>`,
}));

const file: ProjectFile = {
  path: "app.js",
  size_bytes: 30,
  kind: "text",
};

describe("SourceView", () => {
  it("renders the file header with path and line count", () => {
    render(<SourceView file={file} content={"a\nb\nc"} />);
    expect(screen.getByText("app.js")).toBeInTheDocument();
    expect(screen.getByText("3 lines")).toBeInTheDocument();
  });

  it("renders binary placeholder for binary kind", () => {
    render(
      <SourceView
        file={{ path: "font.woff2", size_bytes: 100, kind: "binary" }}
        content=""
      />,
    );
    expect(screen.getByText(/binary file/i)).toBeInTheDocument();
  });

  it("matches the default snapshot", () => {
    const { container } = render(<SourceView file={file} content="hi" />);
    expect(container.firstChild).toMatchSnapshot();
  });
});
