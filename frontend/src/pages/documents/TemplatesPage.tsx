import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useGetDmsTemplatesQuery, useCreateDmsTemplateMutation, useInstantiateTemplateMutation,
} from "../../services/api";
import { useProjectContext } from "../../shell/useProjectContext";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import { useDrawerPeek } from "../../shell/DetailDrawer";
import { promptForValues } from "../../shell/modalService";

type Template = {
  id: string;
  name: string;
  category?: string;
  description?: string;
};

export default function TemplatesPage() {
  const projectId = useProjectContext();
  const { data: templates = [], isLoading, refetch } = useGetDmsTemplatesQuery();
  const [createTpl] = useCreateDmsTemplateMutation();
  const [instantiateTpl] = useInstantiateTemplateMutation();
  const { open: openPeek } = useDrawerPeek();

  const columns = useMemo<ColumnDef<Template, any>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Name",
        cell: (c) => <span style={{ fontWeight: 500 }}>{c.getValue() as string}</span>,
      },
      {
        accessorKey: "category",
        header: "Category",
        cell: (c) => (c.getValue() as string) || "-",
      },
      {
        accessorKey: "description",
        header: "Description",
        cell: (c) => <span style={{ fontSize: "0.82rem", color: "var(--gray-500)" }}>{(c.getValue() as string) || "-"}</span>,
      },
      {
        id: "actions",
        header: "Actions",
        enableSorting: false,
        cell: (c) => {
          const t = c.row.original;
          return (
            <button
              className="btn btn-sm"
              onClick={async (e) => {
                e.stopPropagation();
                const v = await promptForValues({
                  title: "Instantiate template",
                  submitLabel: "Create",
                  fields: [
                    { name: "title", label: "New document title", required: true },
                  ],
                });
                if (!v) return;
                await instantiateTpl({ templateId: t.id, body: { title: v.title, project_id: projectId, vars: {} } });
              }}
            >
              Instantiate
            </button>
          );
        },
      },
    ],
    [instantiateTpl, projectId],
  );

  return (
    <div>
      <PageHeader title="Document templates" subtitle="Reusable document bodies with {{variable}} placeholders." />
      <CommandBar
        items={[
          {
            key: "new", label: "New template", variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "New template",
                submitLabel: "Create",
                fields: [
                  { name: "name", label: "Template name", required: true },
                  { name: "body", label: "Body", kind: "textarea", required: true, rows: 6, helperText: "Use {{var}} placeholders" },
                ],
              });
              if (!v) return;
              await createTpl({ name: v.name, body: v.body });
              refetch();
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={templates as Template[]}
        isLoading={isLoading}
        emptyTitle="No templates yet"
        emptyDescription="Create a template to stamp out consistent document bodies."
        onRowClick={(row) => openPeek("dms-template", row.id)}
      />
    </div>
  );
}
