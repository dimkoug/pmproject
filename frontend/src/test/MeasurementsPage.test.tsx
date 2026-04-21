import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "./test-utils";
import { server } from "./server";
import MeasurementsPage from "../pages/MeasurementsPage";
import { Route, Routes } from "react-router-dom";

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function PageWithRoute() {
  return (
    <Routes>
      <Route path="/projects/:projectId/measurements" element={<MeasurementsPage />} />
    </Routes>
  );
}

const ROUTE = "/projects/11111111-1111-1111-1111-111111111111/measurements";

describe("MeasurementsPage", () => {
  it("renders page title", () => {
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    expect(screen.getByText("Measurement Performance Domain")).toBeInTheDocument();
  });

  it("renders PMBOK reference", () => {
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    expect(screen.getByText(/PMBOK 2.7/)).toBeInTheDocument();
  });

  it("shows measurement from API", async () => {
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    await waitFor(() => {
      expect(screen.getByText("Sprint Velocity")).toBeInTheDocument();
    });
  });

  it("shows metric type badge", async () => {
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    await waitFor(() => {
      expect(screen.getByText("KPI")).toBeInTheDocument();
    });
  });

  it("shows domain badge", async () => {
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    await waitFor(() => {
      expect(screen.getByText("team")).toBeInTheDocument();
    });
  });

  it("opens create modal", async () => {
    const user = userEvent.setup();
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    await user.click(screen.getByText("+ Add Measurement"));
    expect(screen.getByText("Add Measurement")).toBeInTheDocument();
    expect(screen.getByText("Target Value")).toBeInTheDocument();
    expect(screen.getByText("Actual Value")).toBeInTheDocument();
  });
});
