import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "./test-utils";
import { server } from "./server";
import DashboardPage from "../pages/DashboardPage";
import { Route, Routes } from "react-router-dom";

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function DashboardWithRoute() {
  return (
    <Routes>
      <Route path="/projects/:projectId" element={<DashboardPage />} />
    </Routes>
  );
}

const PROJECT_ID = "11111111-1111-1111-1111-111111111111";

describe("DashboardPage", () => {
  it("renders dashboard stats", async () => {
    renderWithProviders(<DashboardWithRoute />, {
      route: `/projects/${PROJECT_ID}`,
    });
    await waitFor(() => {
      expect(screen.getByText("Total Tasks")).toBeInTheDocument();
    });
  });

  it("shows task count", async () => {
    renderWithProviders(<DashboardWithRoute />, {
      route: `/projects/${PROJECT_ID}`,
    });
    await waitFor(() => {
      expect(screen.getByText("Total Tasks")).toBeInTheDocument();
    });
  });

  it("shows open risks card", async () => {
    renderWithProviders(<DashboardWithRoute />, {
      route: `/projects/${PROJECT_ID}`,
    });
    await waitFor(() => {
      expect(screen.getByText("Open Risks")).toBeInTheDocument();
    });
  });

  it("shows stakeholder count card", async () => {
    renderWithProviders(<DashboardWithRoute />, {
      route: `/projects/${PROJECT_ID}`,
    });
    await waitFor(() => {
      expect(screen.getByText("Stakeholders")).toBeInTheDocument();
    });
  });

  it("shows team count card", async () => {
    renderWithProviders(<DashboardWithRoute />, {
      route: `/projects/${PROJECT_ID}`,
    });
    await waitFor(() => {
      expect(screen.getByText("Team Members")).toBeInTheDocument();
    });
  });

  it("shows change requests card", async () => {
    renderWithProviders(<DashboardWithRoute />, {
      route: `/projects/${PROJECT_ID}`,
    });
    await waitFor(() => {
      expect(screen.getByText("Change Requests")).toBeInTheDocument();
    });
  });

  it("shows task distribution table", async () => {
    renderWithProviders(<DashboardWithRoute />, {
      route: `/projects/${PROJECT_ID}`,
    });
    await waitFor(() => {
      expect(screen.getByText("Task Distribution")).toBeInTheDocument();
    });
  });

  it("shows live activity section", async () => {
    renderWithProviders(<DashboardWithRoute />, {
      route: `/projects/${PROJECT_ID}`,
    });
    await waitFor(() => {
      expect(screen.getByText("Live Activity")).toBeInTheDocument();
    });
  });

  it("shows measurement data", async () => {
    renderWithProviders(<DashboardWithRoute />, {
      route: `/projects/${PROJECT_ID}`,
    });
    await waitFor(() => {
      expect(screen.getByText("Key Measurements")).toBeInTheDocument();
    });
  });
});
