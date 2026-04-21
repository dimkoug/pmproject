import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "./test-utils";
import { server } from "./server";
import StakeholdersPage from "../pages/StakeholdersPage";
import { Route, Routes } from "react-router-dom";

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function PageWithRoute() {
  return (
    <Routes>
      <Route path="/projects/:projectId/stakeholders" element={<StakeholdersPage />} />
    </Routes>
  );
}

const ROUTE = "/projects/11111111-1111-1111-1111-111111111111/stakeholders";

describe("StakeholdersPage", () => {
  it("renders page title", () => {
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    expect(screen.getByText("Stakeholder Performance Domain")).toBeInTheDocument();
  });

  it("renders PMBOK reference", () => {
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    expect(screen.getByText(/PMBOK 2.1/)).toBeInTheDocument();
  });

  it("renders add stakeholder button", () => {
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    expect(screen.getByText("+ Add Stakeholder")).toBeInTheDocument();
  });

  it("shows stakeholder data from API", async () => {
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    await waitFor(() => {
      expect(screen.getByText("John Sponsor")).toBeInTheDocument();
    });
  });

  it("shows engagement level", async () => {
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    await waitFor(() => {
      expect(screen.getByText("supportive")).toBeInTheDocument();
    });
  });

  it("shows stakeholder category", async () => {
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    await waitFor(() => {
      expect(screen.getByText("sponsor")).toBeInTheDocument();
    });
  });

  it("opens create modal", async () => {
    const user = userEvent.setup();
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    await user.click(screen.getByText("+ Add Stakeholder"));
    expect(screen.getByText("Add Stakeholder")).toBeInTheDocument();
    expect(screen.getByText("Current Engagement")).toBeInTheDocument();
    expect(screen.getByText("Desired Engagement")).toBeInTheDocument();
    expect(screen.getByText("Expectations")).toBeInTheDocument();
  });
});
