import * as React from "react"
import { Check } from "lucide-react"

import { cn } from "@/lib/utils"

type CheckboxChecked = boolean | "indeterminate"

interface CheckboxProps
  extends Omit<
    React.ButtonHTMLAttributes<HTMLButtonElement>,
    "type" | "onChange" | "value"
  > {
  checked?: CheckboxChecked
  defaultChecked?: CheckboxChecked
  onCheckedChange?: (checked: boolean) => void
}

const Checkbox = React.forwardRef<HTMLButtonElement, CheckboxProps>(
  ({ className, checked, defaultChecked, onCheckedChange, disabled, ...props }, ref) => {
    const isControlled = checked !== undefined
    const [internal, setInternal] = React.useState<CheckboxChecked>(
      defaultChecked ?? false,
    )
    const value = isControlled ? checked : internal
    const isChecked = value === true
    const isMixed = value === "indeterminate"

    function handleClick(e: React.MouseEvent<HTMLButtonElement>) {
      if (disabled) return
      const next = !isChecked
      if (!isControlled) setInternal(next)
      onCheckedChange?.(next)
      props.onClick?.(e)
    }

    return (
      <button
        ref={ref}
        type="button"
        role="checkbox"
        aria-checked={isMixed ? "mixed" : isChecked}
        disabled={disabled}
        onClick={handleClick}
        className={cn(
          "peer h-4 w-4 shrink-0 rounded-sm border border-primary ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
          isChecked && "bg-primary text-primary-foreground",
          className,
        )}
        {...props}
      >
        {isChecked && (
          <Check className="h-3.5 w-3.5 mx-auto" strokeWidth={3} />
        )}
      </button>
    )
  },
)
Checkbox.displayName = "Checkbox"

export { Checkbox }
