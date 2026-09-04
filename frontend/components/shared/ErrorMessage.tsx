export function ErrorMessage({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <div className="bg-danger-100 border border-danger-600/30 text-danger-600 text-sm rounded-md px-3 py-2">
      {message}
    </div>
  );
}
