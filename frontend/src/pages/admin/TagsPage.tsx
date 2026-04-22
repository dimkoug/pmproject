import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useGetTagsQuery,
  useCreateTagMutation,
  useUpdateTagMutation,
  useDeleteTagMutation,
} from "../../services/api";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import DataTable from "../../shell/DataTable";
import TagChip from "../../shell/TagChip";
import { promptForValues, confirmAction } from "../../shell/modalService";

type Tag = {
  id: string;
  name: string;
  color?: string | null;
  description?: string | null;
};

const COLOR_PRESETS = [
  { value: "#4f46e5", label: "Indigo" },
  { value: "#0ea5e9", label: "Sky" },
  { value: "#059669", label: "Emerald" },
  { value: "#f59e0b", label: "Amber" },
  { value: "#ef4444", label: "Red" },
  { value: "#7c3aed", label: "Violet" },
  { value: "#ec4899", label: "Pink" },
  { value: "#14b8a6", label: "Teal" },
  { value: "#6b7280", label: "Gray" },
];

export default function TagsPage() {
  const { data: tags = [], isLoading } = useGetTagsQuery();
  const [createTag] = useCreateTagMutation();
  const [updateTag] = useUpdateTagMutation();
  const [deleteTag] = useDeleteTagMutation();

  const columns = useMemo<ColumnDef<Tag, any>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Tag",
        cell: (c) => <TagChip tag={c.row.original} size="md" />,
      },
      {
        accessorKey: "color",
        header: "Color",
        cell: (c) => {
          const v = c.getValue() as string | null | undefined;
          return v ? (
            <span style={{ fontFamily: "monospace", fontSize: "0.78rem", color: "var(--gray-500)" }}>{v}</span>
          ) : (
            "-"
          );
        },
      },
      {
        accessorKey: "description",
        header: "Description",
        cell: (c) => (c.getValue() as string) || "-",
      },
      {
        id: "actions",
        header: "Actions",
        enableSorting: false,
        cell: (c) => {
          const row = c.row.original;
          return (
            <div style={{ display: "inline-flex", gap: "0.25rem" }} onClick={(e) => e.stopPropagation()}>
              <button
                className="btn btn-sm"
                onClick={async () => {
                  const v = await promptForValues({
                    title: `Edit tag "${row.name}"`,
                    submitLabel: "Save",
                    fields: [
                      { name: "name", label: "Name", required: true, defaultValue: row.name },
                      { name: "color", label: "Color", kind: "select", options: COLOR_PRESETS, defaultValue: row.color || "" },
                      { name: "description", label: "Description", kind: "textarea", defaultValue: row.description || "" },
                    ],
                  });
                  if (!v) return;
                  await updateTag({
                    id: row.id,
                    body: {
                      name: v.name,
                      color: v.color || null,
                      description: v.description || null,
                    },
                  });
                }}
              >
                Edit
              </button>
              <button
                className="btn btn-sm btn-danger"
                onClick={async () => {
                  const ok = await confirmAction({
                    title: `Delete tag "${row.name}"?`,
                    description: "This removes the tag and all its attachments everywhere.",
                    submitLabel: "Delete",
                    dangerous: true,
                  });
                  if (!ok) return;
                  await deleteTag(row.id);
                }}
              >
                Delete
              </button>
            </div>
          );
        },
      },
    ],
    [updateTag, deleteTag],
  );

  return (
    <div>
      <PageHeader
        title="Tags"
        subtitle="Cross-cutting labels you can attach to any document, lead, opportunity, invoice, or task."
        breadcrumbs={[{ to: "/admin", label: "Admin" }, { label: "Tags" }]}
      />
      <CommandBar
        items={[
          {
            key: "new",
            label: "New tag",
            variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "New tag",
                submitLabel: "Create",
                fields: [
                  { name: "name", label: "Name", required: true, placeholder: "e.g. urgent" },
                  { name: "color", label: "Color", kind: "select", options: COLOR_PRESETS, defaultValue: "#4f46e5" },
                  { name: "description", label: "Description", kind: "textarea" },
                ],
              });
              if (!v) return;
              await createTag({
                name: v.name,
                color: v.color || undefined,
                description: v.description || undefined,
              });
            },
          },
        ]}
      />
      <DataTable
        columns={columns}
        data={tags as Tag[]}
        isLoading={isLoading}
        emptyTitle="No tags yet"
        emptyDescription="Create your first tag to label and filter records across the app."
      />
    </div>
  );
}
