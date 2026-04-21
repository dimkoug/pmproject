import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "./test-utils";
import { server } from "./server";
import ChangeRequestsPage from "../pages/ChangeRequestsPage";
import { Route, Routes } from "react-router-dom";

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function PageWithRoute() {
  return (
    <Routes>
      <Route path="/projects/:projectId/changes" element={<ChangeRequestsPage />} />
    </Routes>
  );
}

const ROUTE = "/projects/11111111-1111-1111-1111-111111111111/changes";

describe("ChangeRequestsPage", () => {
  it("renders page title", () => {
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    expect(screen.getByText("Change Management")).toBeInTheDocument();
  });

  it("renders PMBOK reference", () => {
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    expect(screen.getByText(/PMBOK Principle 3.12/)).toBeInTheDocument();
  });

  it("shows change request from API", async () => {
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    await waitFor(() => {
      expect(screen.getByText("Add OAuth2 support")).toBeInTheDocument();
    });
  });

  it("shows impact badge", async () => {
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    await waitFor(() => {
      expect(screen.getByText("high")).toBeInTheDocument();
    });
  });

  it("shows justification", async () => {
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    await waitFor(() => {
      expect(screen.getByText("Customer requirement")).toBeInTheDocument();
    });
  });

  it("opens create modal", async () => {
    const user = userEvent.setup();
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    await user.click(screen.getByText("+ New Change Request"));
    expect(screen.getByText("Submit Change Request")).toBeInTheDocument();
    expect(screen.getByText("Impact Level")).toBeInTheDocument();
    expect(screen.getByText("Impact Analysis")).toBeInTheDocument();
  });
});
