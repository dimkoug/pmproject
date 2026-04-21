import {
  useGetOpportunitiesQuery, useCreateOpportunityMutation, useUpdateOpportunityStageMutation,
} from "../../services/api";
import BoardContainer from "../../components/dnd/BoardContainer";
import BoardColumn from "../../components/dnd/BoardColumn";
import DraggableCard from "../../components/dnd/DraggableCard";
import PageHeader from "../../shell/PageHeader";
import CommandBar from "../../shell/CommandBar";

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
              const title = prompt("Opportunity title:"); if (!title) return;
              const amount = parseFloat(prompt("Amount:") || "0");
              const probability = parseInt(prompt("Probability (0-100):") || "50");
              await createOpp({ title, amount, probability });
              refetch();
            },
          },
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
