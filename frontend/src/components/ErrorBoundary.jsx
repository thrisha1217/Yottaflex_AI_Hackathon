import React from "react";
import { ErrorMessage } from "./ErrorMessage";

/**
 * ErrorBoundary — class component that wraps pages/sections.
 *
 * On an unhandled render error it displays an inline <ErrorMessage>
 * instead of crashing the whole page. Errors are also logged to the console.
 *
 * Usage:
 *   <ErrorBoundary>
 *     <SomeComponent />
 *   </ErrorBoundary>
 */
class ErrorBoundary extends React.Component {
  state = { hasError: false, error: null };

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error("ErrorBoundary caught an error:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: "1rem" }}>
          <ErrorMessage error={this.state.error} />
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
export { ErrorBoundary };
