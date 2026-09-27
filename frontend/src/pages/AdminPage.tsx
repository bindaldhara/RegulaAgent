import { Link } from "react-router-dom";
import { AmbientBackground } from "../components/AmbientBackground";
import { EvalPanel } from "../components/EvalPanel";

export function AdminPage() {
  return (
    <div className="relative flex min-h-screen flex-col text-zinc-100">
      <AmbientBackground />
      <header className="relative z-10 shrink-0 border-b border-white/5 bg-black/20 backdrop-blur-md">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-4 px-4 py-4 md:px-6">
          <div>
            <p className="text-[10px] font-medium uppercase tracking-wider text-violet-300/80">Admin</p>
            <h1 className="text-lg font-semibold text-white">Evaluation suite</h1>
          </div>
          <Link
            to="/"
            className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-medium text-zinc-200 hover:bg-white/10"
          >
            ← Patient chat
          </Link>
        </div>
      </header>
      <main className="relative z-10 mx-auto flex min-h-0 w-full max-w-3xl flex-1 flex-col px-4 py-6 md:px-6">
        <EvalPanel className="min-h-0 flex-1" />
      </main>
    </div>
  );
}
