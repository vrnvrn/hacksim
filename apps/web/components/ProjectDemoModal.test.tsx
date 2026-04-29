import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ProjectDemoModal } from "./ProjectDemoModal";
import type { Project } from "@/lib/types";

const project: Project = {
  id: "proj_d3vis",
  team_id: "team_alpha",
  bounty_id: "bnty_1",
  title: "Permit Two-Tap",
  tagline: "Two taps from idle to signed permit.",
  description: "",
  status: "submitted",
  submitted_at: "2026-04-28T12:00:00Z",
  commit_hash: "7f3a2c9deadbeef1234567890",
  entry_path: "index.html",
  artefact_path: "/x",
  github_url: null,
};

const filesPayload = {
  project_id: "proj_d3vis",
  commit_hash: "7f3a2c9deadbeef1234567890",
  entry_path: "index.html",
  github_url: null,
  files: [
    { path: "index.html", size_bytes: 100, kind: "text" },
    { path: "app.js", size_bytes: 200, kind: "text" },
  ],
};

beforeEach(() => {
  vi.stubEnv("NEXT_PUBLIC_USE_MOCKS", "true");
  global.fetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : input.toString();
    if (url.includes("/files") && !url.match(/\/files\/.+/)) {
      return new Response(JSON.stringify(filesPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    if (url.match(/\/files\/.+/)) {
      return new Response("<html>hello</html>", { status: 200 });
    }
    return new Response("", { status: 404 });
  }) as unknown as typeof fetch;
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

describe("ProjectDemoModal", () => {
  it("renders the title and three tabs when open", async () => {
    render(
      <ProjectDemoModal
        simId="sim_x"
        projectId="proj_d3vis"
        open
        onClose={() => {}}
        project={project}
      />,
    );
    await waitFor(() =>
      expect(screen.getByRole("tab", { name: "Demo" })).toBeInTheDocument(),
    );
    expect(screen.getByRole("tab", { name: "Code" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Verdict" })).toBeInTheDocument();
  });

  it("switches tabs on click", async () => {
    const user = userEvent.setup();
    render(
      <ProjectDemoModal
        simId="sim_x"
        projectId="proj_d3vis"
        open
        onClose={() => {}}
        project={project}
      />,
    );
    const codeTab = await screen.findByRole("tab", { name: "Code" });
    await user.click(codeTab);
    await waitFor(() =>
      expect(codeTab).toHaveAttribute("data-state", "active"),
    );
  });

  it("renders the iframe with allow-scripts only", async () => {
    render(
      <ProjectDemoModal
        simId="sim_x"
        projectId="proj_d3vis"
        open
        onClose={() => {}}
        project={project}
      />,
    );
    const frame = await screen.findByTitle(/demo of permit two-tap/i);
    expect(frame).toHaveAttribute("sandbox", "allow-scripts");
  });

  it("matches the default snapshot when open", async () => {
    const { baseElement } = render(
      <ProjectDemoModal
        simId="sim_x"
        projectId="proj_d3vis"
        open
        onClose={() => {}}
        project={project}
      />,
    );
    await screen.findByRole("tab", { name: "Demo" });
    expect(baseElement).toMatchSnapshot();
  });
});
