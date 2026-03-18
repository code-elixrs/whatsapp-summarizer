import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { describe, it, expect } from "vitest";
import { App } from "../App";

describe("App", () => {
  it("renders without crashing", () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );
    expect(screen.getByText("LifeLog")).toBeInTheDocument();
  });

  it("shows spaces heading on home page", () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );
    expect(screen.getByText("Spaces")).toBeInTheDocument();
  });
});
