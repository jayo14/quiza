import { useState } from "react";
import { BrowserRouter, Routes, Route, Outlet, Navigate } from "react-router-dom";

import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import Dashboard from "./components/Dashboard";
import UploadMaterial from "./components/UploadMaterial";
import MyQuizzes from "./components/MyQuizzes";
import Quiz from "./components/Quiz";
import Summary from "./components/Summary";
import Progress from "./components/Progress";
import Settings from "./components/Settings";
import ReviewAnswers from "./components/ReviewAnswers";

import SignIn from "./components/SignIn";
import SignUp from "./components/SignUp";
import ForgotPassword from "./components/ForgotPassword";
import ResetPassword from "./components/ResetPassword";

import { Toaster } from "sonner";
import ServerWarmupBanner from "./components/ServerWarmupBanner";

import { AuthProvider, useAuth } from "./context/AuthContext";

import "./App.css";

function ProtectedRoute() {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="app-loading">Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/signin" replace />;
  }

  return <Outlet />;
}

function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="app">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="main-area">
        <Header onToggleMenu={() => setSidebarOpen((prev) => !prev)} />
        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <Toaster position="top-center" />
      <ServerWarmupBanner />
      <BrowserRouter>
        <Routes>
          <Route path="/signin" element={<SignIn />} />
          <Route path="/signup" element={<SignUp />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />

          <Route element={<ProtectedRoute />}>
            <Route element={<DashboardLayout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/upload" element={<UploadMaterial />} />
              <Route path="/quizzes" element={<MyQuizzes />} />
              <Route path="/quiz" element={<Quiz />} />
              <Route path="/summary" element={<Summary />} />
              <Route path="/progress" element={<Progress />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/review" element={<ReviewAnswers />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
