import {
  useGetOpportunitiesQuery, useCreateOpportunityMutation, useUpdateOpportunityStageMutation,
} from "../../services/api";
import BoardContainer from "../../components/dnd/BoardContainer";
import BoardColumn from "../../components/dnd/BoardColumn";
import DraggableCard from "../../components/dnd/DraggableCard";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";
import { downloadCsv } from "../../shell/csvExport";
import { promptForValues } from "../../shell/modalService";

const OPP_STAGES = ["prospecting", "qualification", "proposal", "negotiation", "closed_won", "closed_lost"];

export default function OpportunitiesPage() {
  const { data: opps = [], refetch } = useGetOpportunitiesQuery();
  const [createOpp] = useCreateOpportunityMutation();
  const [updateStage] = useUpdateOpportunityStageMutation();

  return (
    <div>
      <PageHeader title="Opportunities" subtitle="Drag cards between stages to progress the pipeline." />
      <CommandBar
        items={[
          {
            key: "new", label: "New opportunity", variant: "primary",
            onClick: async () => {
              const v = await promptForValues({
                title: "New opportunity",
                submitLabel: "Create",
                fields: [
                  { name: "title", label: "Opportunity title", required: true },
                  { name: "amount", label: "Amount", kind: "number", step: 0.01 },
                  { name: "probability", label: "Probability (0-100)", kind: "number", min: 0, max: 100, defaultValue: "50" },
                ],
              });
              if (!v) return;
              const amount = parseFloat(v.amount || "0");
              const probability = parseInt(v.probability || "50");
              await createOpp({ title: v.title, amount, probability });
              refetch();
            },
          },
          { key: "export", label: "Export CSV", onClick: () => downloadCsv("opportunities") },
        ]}
      />
      <BoardContainer
        onDragEnd={(itemId, newStage) => { updateStage({ id: itemId, stage: newStage }); refetch(); }}
        renderOverlay={(activeId) => {
          const o = opps.find((x: any) => x.id === activeId);
          return o ? <div className="board-card" style={{ opacity: 0.9, boxShadow: "0 8px 24px rgba(0,0,0,0.15)", width: 240 }}><div className="title">{o.title}</div></div> : null;
        }}
      >
        <div className="board">
          {OPP_STAGES.map((stage) => (
            <BoardColumn key={stage} id={stage} title={stage.replace(/_/g, " ")} count={opps.filter((o: any) => o.stage === stage).length}>
              {opps.filter((o: any) => o.stage === stage).map((o: any) => (
                <DraggableCard key={o.id} id={o.id}>
                  <div className="title">{o.title}</div>
                  <div className="meta">{o.amount ? `$${o.amount.toLocaleString()}` : ""} {o.probability ? `${o.probability}%` : ""}</div>
                </DraggableCard>
              ))}
            </BoardColumn>
          ))}
        </div>
      </BoardContainer>
    </div>
  );
}
