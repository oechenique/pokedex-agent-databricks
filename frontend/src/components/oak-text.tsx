import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Las respuestas reales de Oak vienen en markdown (tablas, negrita, listas
// -- ver las transcripciones de Fase 4/5). Sin esto se verían los asteriscos
// y pipes crudos en la burbuja.
export default function OakText({ text }: { text: string }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
  );
}
