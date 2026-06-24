import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import { FileText, Layers, MessagesSquare, Clock, Gauge, Coins, ThumbsUp, Loader2 } from "lucide-react";
import { Card } from "@/components/ui";
import { getAnalytics } from "@/services/api";
import type { Analytics } from "@/services/types";

function Stat({ icon: Icon, label, value }: { icon: any; label: string; value: string | number }) {
  return (
    <Card className="flex items-center gap-3 p-4">
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent text-accent-foreground">
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-xl font-semibold tabular-nums">{value}</p>
      </div>
    </Card>
  );
}

const PIE_COLORS = ["#22c55e", "#ef4444"];

export function AnalyticsPage() {
  const [data, setData] = useState<Analytics | null>(null);

  useEffect(() => {
    getAnalytics().then(setData).catch(() => setData(null));
  }, []);

  if (!data)
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground"><Loader2 className="h-6 w-6 animate-spin" /></div>
    );

  const ragas = data.average_ragas;
  const ragasData = [
    { name: "Faithfulness", value: +(ragas.faithfulness * 100).toFixed(0) },
    { name: "Answer Rel.", value: +(ragas.answer_relevancy * 100).toFixed(0) },
    { name: "Ctx Precision", value: +(ragas.context_precision * 100).toFixed(0) },
  ];
  const fb = [
    { name: "Helpful", value: data.feedback.up },
    { name: "Not helpful", value: data.feedback.down },
  ];

  return (
    <div className="scrollbar-thin h-full overflow-y-auto">
      <div className="mx-auto max-w-5xl px-4 py-6">
        <h1 className="text-xl font-semibold">Analytics</h1>
        <p className="mt-1 text-sm text-muted-foreground">Usage, retrieval quality, and feedback at a glance.</p>

        <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
          <Stat icon={FileText} label="Documents" value={data.total_documents} />
          <Stat icon={Layers} label="Chunks" value={data.total_chunks} />
          <Stat icon={MessagesSquare} label="Conversations" value={data.total_conversations} />
          <Stat icon={Clock} label="Avg response" value={`${data.average_response_time.toFixed(1)}s`} />
          <Stat icon={Gauge} label="Avg faithfulness" value={ragas.faithfulness.toFixed(2)} />
          <Stat icon={Coins} label="Total tokens" value={data.token_usage.total_tokens ?? 0} />
          <Stat icon={ThumbsUp} label="Positive feedback" value={data.feedback.up} />
        </div>

        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          <Card className="p-4">
            <h2 className="mb-3 text-sm font-semibold">Average RAGAS scores (%)</h2>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={ragasData}>
                <XAxis dataKey="name" tick={{ fontSize: 12, fill: "currentColor" }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 12, fill: "currentColor" }} />
                <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8 }} />
                <Bar dataKey="value" fill="hsl(var(--primary))" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Card className="p-4">
            <h2 className="mb-3 text-sm font-semibold">Feedback</h2>
            {data.feedback.up + data.feedback.down === 0 ? (
              <p className="py-10 text-center text-sm text-muted-foreground">No feedback yet.</p>
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={fb} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label>
                    {fb.map((_, i) => <Cell key={i} fill={PIE_COLORS[i]} />)}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            )}
          </Card>
        </div>

        <Card className="mt-4 p-4">
          <h2 className="mb-3 text-sm font-semibold">Top questions</h2>
          {data.top_questions.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">No queries logged yet.</p>
          ) : (
            <ol className="space-y-1.5">
              {data.top_questions.map((q, i) => (
                <li key={i} className="flex items-center justify-between gap-3 rounded-md px-2 py-1.5 text-sm hover:bg-secondary/50">
                  <span className="min-w-0 flex-1 truncate">{i + 1}. {q.question}</span>
                  <span className="shrink-0 rounded-full bg-accent px-2 py-0.5 text-xs text-accent-foreground">{q.count}×</span>
                </li>
              ))}
            </ol>
          )}
        </Card>
      </div>
    </div>
  );
}
