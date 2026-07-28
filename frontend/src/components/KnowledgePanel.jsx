import { Empty, Info, MiniList, StepCard } from "./common.jsx";

export function KnowledgePanel({ knowledgeBase, documents, busy, onUpload }) {
  return (
    <StepCard number="01" title="知识库与资料入库" tone="blue">
      <p>刷新页面会自动恢复最近一个有资料的知识库、资料列表和本机用户画像。</p>
      <Info label="Knowledge Base" value={knowledgeBase?.id ?? "尚未创建"} />
      <label className={`upload ${!knowledgeBase || busy ? "disabled" : ""}`}>
        上传学习资料
        <input type="file" onChange={onUpload} disabled={!knowledgeBase || busy} />
      </label>
      <MiniList
        items={documents.map((item) => `${item.original_filename} · ${item.status}`)}
        empty="暂无上传资料"
      />
    </StepCard>
  );
}
