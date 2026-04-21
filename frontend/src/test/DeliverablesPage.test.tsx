import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "./test-utils";
import { server } from "./server";
import DeliverablesPage from "../pages/DeliverablesPage";
import { Route, Routes } from "react-router-dom";

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function PageWithRoute() {
  return (
    <Routes>
      <Route path="/projects/:projectId/deliverables" element={<DeliverablesPage />} />
    </Routes>
  );
}

const ROUTE = "/projects/11111111-1111-1111-1111-111111111111/deliverables";

describe("DeliverablesPage", () => {
  it("renders page title", () => {
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    expect(screen.getByText("Delivery Performance Domain")).toBeInTheDocument();
  });

  it("renders PMBOK reference", () => {
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    expect(screen.getByText(/PMBOK 2.6/)).toBeInTheDocument();
  });

  it("shows deliverable from API", async () => {
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    await waitFor(() => {
      expect(screen.getByText("API Module")).toBeInTheDocument();
    });
  });

  it("shows acceptance criteria", async () => {
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    await waitFor(() => {
      expect(screen.getByText(/All endpoints tested/)).toBeInTheDocument();
    });
  });

  it("opens create modal", async () => {
    const user = userEvent.setup();
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    await user.click(screen.getByText("+ Add Deliverable"));
    expect(screen.getByText("Add Deliverable")).toBeInTheDocument();
    expect(screen.getByText("Acceptance Criteria")).toBeInTheDocument();
  });
});
