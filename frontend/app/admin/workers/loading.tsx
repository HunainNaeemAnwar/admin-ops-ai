import { Skeleton } from "@/components/ui/skeleton"

export default function WorkersLoading() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-8 w-48" />
      {Array.from({ length: 8 }).map((_, i) => (
        <Skeleton key={i} className="h-10 w-64" />
      ))}
    </div>
  )
}
