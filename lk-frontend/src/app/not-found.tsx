import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-surface">
      <div className="text-center">
        <p className="text-6xl font-bold text-primary">404</p>
        <h1 className="mt-4 text-xl font-semibold text-gray-900">Страница не найдена</h1>
        <p className="mt-2 text-text-muted">Возможно, она была перемещена или удалена.</p>
        <div className="mt-8 flex justify-center gap-4">
          <Link
            href="/dashboard"
            className="px-6 py-2.5 bg-accent text-text-on-dark rounded-xl text-sm font-medium hover:bg-accent-hover"
          >
            На главную
          </Link>
        </div>
      </div>
    </div>
  );
}
