import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-surface">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-primary mb-4">404</h1>
        <p className="text-text-muted mb-6">Страница не найдена</p>
        <Link href="/leads" className="px-6 py-3 bg-accent text-text-on-dark rounded-lg text-sm font-medium hover:bg-accent-hover">
          На главную
        </Link>
      </div>
    </div>
  );
}
