const colors = [
  "bg-blue-600 text-white",
  "bg-emerald-600 text-white",
  "bg-purple-600 text-white",
  "bg-orange-600 text-white",
  "bg-pink-600 text-white",
  "bg-cyan-600 text-white",
  "bg-red-600 text-white",
  "bg-indigo-600 text-white",
]

function getInitial(name: string): string {
  return name.charAt(0).toUpperCase()
}

function getColor(name: string): string {
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return colors[Math.abs(hash) % colors.length]
}

interface AvatarProps {
  name: string
  size?: "sm" | "md" | "lg"
  className?: string
}

const sizes = {
  sm: "h-7 w-7 text-xs",
  md: "h-9 w-9 text-sm",
  lg: "h-11 w-11 text-base",
}

export function Avatar({ name, size = "md", className = "" }: AvatarProps) {
  return (
    <div
      className={`inline-flex items-center justify-center rounded-full font-semibold ${getColor(name)} ${sizes[size]} ${className}`}
      aria-hidden="true"
    >
      {getInitial(name)}
    </div>
  )
}
