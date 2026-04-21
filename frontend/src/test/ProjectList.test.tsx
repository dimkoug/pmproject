import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "./test-utils";
import { server } from "./server";
import ProjectList from "../pages/ProjectList";

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("ProjectList", () => {
  it("renders the page title", async () => {
    renderWithProviders(<ProjectList />);
    await waitFor(() => {
      expect(screen.getByText("PMBOK Project Management")).toBeInTheDocument();
    });
  });

  it("renders the PMBOK subtitle", async () => {
    renderWithProviders(<ProjectList />);
    await waitFor(() => {
      expect(screen.getByText(/Based on PMBOK 7th Edition/)).toBeInTheDocument();
    });
  });

  it("renders the new project button", async () => {
    renderWithProviders(<ProjectList />);
    await waitFor(() => {
      expect(screen.getByText("+ New Project")).toBeInTheDocument();
    });
  });

  it("shows project list from API", async () => {
    renderWithProviders(<ProjectList />);
    await waitFor(() => {
      expect(screen.getByText("PMBOK Test Project")).toBeInTheDocument();
    });
  });

  it("shows project status badge", async () => {
    renderWithProviders(<ProjectList />);
    await waitFor(() => {
      expect(screen.getByText("executing")).toBeInTheDocument();
    });
  });

  it("shows development approach badge", async () => {
    renderWithProviders(<ProjectList />);
    await waitFor(() => {
      expect(screen.getByText("agile")).toBeInTheDocument();
    });
  });

  it("opens create modal on button click", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ProjectList />);
    await waitFor(() => screen.getByText("+ New Project"));
    await user.click(screen.getByText("+ New Project"));
    expect(screen.getByText("Create Project")).toBeInTheDocument();
    expect(screen.getByText("Project Name")).toBeInTheDocument();
  });

  it("shows development approach dropdown in create modal", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ProjectList />);
    await waitFor(() => screen.getByText("+ New Project"));
    await user.click(screen.getByText("+ New Project"));
    expect(screen.getByText("Development Approach")).toBeInTheDocument();
  });

  it("closes modal on cancel click", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ProjectList />);
    await waitFor(() => screen.getByText("+ New Project"));
    await user.click(screen.getByText("+ New Project"));
    expect(screen.getByText("Create Project")).toBeInTheDocument();
    await user.click(screen.getByText("Cancel"));
    expect(screen.queryByText("Create Project")).not.toBeInTheDocument();
  });

  it("shows delete button for each project", async () => {
    renderWithProviders(<ProjectList />);
    await waitFor(() => {
      expect(screen.getByText("Delete")).toBeInTheDocument();
    });
  });
});
