type Props = { title: string; milestone: string };

// Shell page until the lens view lands. Content comes from /v1/view in M5/M6.
export default function Placeholder({ title, milestone }: Props) {
  return (
    <section className="space-y-2">
      <h1 className="text-2xl font-semibold">{title}</h1>
      <p className="text-slate-500">This view is built in {milestone}.</p>
    </section>
  );
}
