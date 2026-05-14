import { Navigate, useParams } from "react-router-dom";

export function WorkspaceIndexRedirect() {
  const { workspaceId } = useParams();
  return <Navigate to={`/app/workspace/${workspaceId}/dashboard`} replace />;
}
