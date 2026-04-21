import { useParams, useSearchParams } from "react-router-dom";

export function useProjectContext(): string | undefined {
  const params = useParams();
  const [search] = useSearchParams();
  return params.projectId || search.get("project") || undefined;
}
