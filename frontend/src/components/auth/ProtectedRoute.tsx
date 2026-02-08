import { Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import LoadingSpinner from "@/components/common/LoadingSpinner";

interface Props {
  children: React.ReactNode;
  requireSuperuser?: boolean;
}

export default function ProtectedRoute({ children, requireSuperuser }: Props) {
  const { user, isAuthenticated, loading } = useAuth();

  if (loading) return <LoadingSpinner />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (requireSuperuser && !user?.is_superuser) return <Navigate to="/" replace />;

  return <>{children}</>;
}
