import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { FileTree } from "./FileTree";
import type { ProjectFile } from "@/lib/types";

const files: ProjectFile[] = [
  { path: "index.html", size_bytes: 100, kind: "text" },
  { path: "style.css", size_bytes: 50, kind: "text" },
  { path: "app.js", size_bytes: 200, kind: "text" },
  { path: "assets/logo.svg", size_bytes: 300, kind: "image" },
];

describe("FileTree", () => {
  it("renders top-level files and a folder", () => {
    render(
      <FileTree files={files} selectedPath="index.html" onSelect={() => {}} />,
    );
    expect(screen.getByText("index.html")).toBeInTheDocument();
    expect(screen.getByText("style.css")).toBeInTheDocument();
    expect(screen.getByText("assets")).toBeInTheDocument();
  });

  it("calls onSelect when a file is clicked", () => {
    const onSelect = vi.fn();
    render(
      <FileTree files={files} selectedPath="index.html" onSelect={onSelect} />,
    );
    fireEvent.click(screen.getByText("style.css"));
    expect(onSelect).toHaveBeenCalledWith("style.css");
  });

  it("matches the default snapshot", () => {
    const { container } = render(
      <FileTree files={files} selectedPath="index.html" onSelect={() => {}} />,
    );
    expect(container.firstChild).toMatchSnapshot();
  });
});
