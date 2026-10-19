import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import Layout from "./components/Layout";
import { Loading } from "./components/ui";
import Landing from "./pages/Landing";
import { Login, Register } from "./pages/Auth";
import Onboarding from "./pages/Onboarding";
const Dashboard = lazy(() => import("./pages/Dashboard"));
const DietPlan = lazy(() => import("./pages/DietPlan"));
const Meals = lazy(() => import("./pages/Meals"));
const Workouts = lazy(() => import("./pages/Workouts"));
const FoodScanner = lazy(() => import("./pages/FoodScanner"));
const Assistant = lazy(() => import("./pages/Assistant"));
const KnowledgeBase = lazy(() => import("./pages/KnowledgeBase"));
const Progress = lazy(() => import("./pages/Progress"));
const AILab = lazy(() => import("./pages/AILab"));
const Profile = lazy(() => import("./pages/Profile"));

function Protected({ children }) {
  const { user, profile, loading } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (loading || !profile) return <Loading text="Loading your profile..." />;
  if (!profile.onboarded) return <Navigate to="/onboarding" replace />;
  return children;
}

function GuestOnly({ children }) {
  const { user } = useAuth();
  return user ? <Navigate to="/app" replace /> : children;
}

export default function App() {
  const { user, profile, loading } = useAuth();
  return (
    <Suspense fallback={<Loading />}>
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<GuestOnly><Login /></GuestOnly>} />
      <Route path="/register" element={<GuestOnly><Register /></GuestOnly>} />
      <Route path="/onboarding" element={!user ? <Navigate to="/login" replace /> : loading || !profile ? <Loading /> : <Onboarding />} />
      <Route path="/app" element={<Protected><Layout /></Protected>}>
        <Route index element={<Dashboard />} />
        <Route path="plan" element={<DietPlan />} />
        <Route path="meals" element={<Meals />} />
        <Route path="workouts" element={<Workouts />} />
        <Route path="assistant" element={<Assistant />} />
        <Route path="scanner" element={<FoodScanner />} />
        <Route path="knowledge" element={<KnowledgeBase />} />
        <Route path="progress" element={<Progress />} />
        <Route path="lab" element={<AILab />} />
        <Route path="profile" element={<Profile />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
    </Suspense>
  );
}
