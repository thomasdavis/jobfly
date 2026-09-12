import { lazy, Suspense } from "react";
import { sessionId } from "./api";
import Onboarding from "./components/Onboarding";
const SessionApp = lazy(() => import("./SessionApp"));
export default function App() {
  return sessionId ? <Suspense fallback={<div className="route-loading" role="status">Loading your session…</div>}><SessionApp /></Suspense> : <Onboarding />;
}
