import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "./test-utils";
import { server } from "./server";
import RisksPage from "../pages/RisksPage";
import { Route, Routes } from "react-router-dom";

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function PageWithRoute() {
  return (
    <Routes>
      <Route path="/projects/:projectId/risks" element={<RisksPage />} />
    </Routes>
  );
}

const ROUTE = "/projects/11111111-1111-1111-1111-111111111111/risks";

describe("RisksPage", () => {
  it("renders page title", () => {
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    expect(screen.getByText("Uncertainty Performance Domain")).toBeInTheDocument();
  });

  it("renders PMBOK reference", () => {
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    expect(screen.getByText(/PMBOK 2.8/)).toBeInTheDocument();
  });

  it("shows risk data from API", async () => {
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    await waitFor(() => {
      expect(screen.getByText("Key person dependency")).toBeInTheDocument();
    });
  });

  it("shows risk category", async () => {
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    await waitFor(() => {
      expect(screen.getByText("organizational")).toBeInTheDocument();
    });
  });

  it("shows probability badge", async () => {
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    await waitFor(() => {
      expect(screen.getByText("high")).toBeInTheDocument();
    });
  });

  it("shows impact badge", async () => {
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    await waitFor(() => {
      expect(screen.getByText("very high")).toBeInTheDocument();
    });
  });

  it("shows strategy", async () => {
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    await waitFor(() => {
      expect(screen.getByText("mitigate")).toBeInTheDocument();
    });
  });

  it("opens create modal", async () => {
    const user = userEvent.setup();
    renderWithProviders(<PageWithRoute />, { route: ROUTE });
    await user.click(screen.getByText("+ Add Risk"));
    expect(screen.getByText("Add Risk")).toBeInTheDocument();
    expect(screen.getByText("Response Plan")).toBeInTheDocument();
    expect(screen.getByText("Trigger Conditions")).toBeInTheDocument();
  });
});
