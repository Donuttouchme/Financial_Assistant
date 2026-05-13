import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useCreateImportPreset,
  useDeleteImportPreset,
  useImportPresets,
} from "@/hooks/queries/useImportPresets";
import type { CsvImportConfig } from "@/api/types";

interface Props {
  currentConfig: CsvImportConfig;
  onLoad: (config: CsvImportConfig) => void;
}

export function PresetSelector({ currentConfig, onLoad }: Props) {
  const { data: presets } = useImportPresets();
  const create = useCreateImportPreset();
  const remove = useDeleteImportPreset();

  const [selectedId, setSelectedId] = useState<string>("");
  const [newName, setNewName] = useState("");

  function handleLoad(idStr: string) {
    setSelectedId(idStr);
    const p = (presets ?? []).find((x) => x.id === Number(idStr));
    if (p) onLoad(p.config);
  }

  async function handleSave() {
    if (!newName.trim()) {
      toast.error("Name required");
      return;
    }
    try {
      await create.mutateAsync({
        name: newName.trim(),
        config: currentConfig,
      });
      toast.success(`Preset '${newName}' saved`);
      setNewName("");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Save failed";
      toast.error(msg);
    }
  }

  async function handleDelete() {
    if (!selectedId) return;
    try {
      await remove.mutateAsync(Number(selectedId));
      setSelectedId("");
      toast.success("Preset deleted");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Delete failed";
      toast.error(msg);
    }
  }

  return (
    <div className="flex items-end gap-2 flex-wrap">
      <div className="space-y-1">
        <div className="text-xs text-muted-foreground">Load preset</div>
        <Select value={selectedId} onValueChange={handleLoad}>
          <SelectTrigger className="w-44" aria-label="Load preset">
            <SelectValue placeholder="—" />
          </SelectTrigger>
          <SelectContent>
            {(presets ?? []).map((p) => (
              <SelectItem key={p.id} value={String(p.id)}>
                {p.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <Button
        type="button"
        variant="ghost"
        disabled={!selectedId}
        onClick={handleDelete}
      >
        Delete
      </Button>

      <div className="space-y-1 ml-auto">
        <div className="text-xs text-muted-foreground">
          Save current config as preset
        </div>
        <div className="flex gap-2">
          <Input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="UBS"
            className="w-32"
            aria-label="Preset name"
          />
          <Button
            type="button"
            onClick={handleSave}
            disabled={create.isPending}
          >
            {create.isPending ? "Saving…" : "Save as preset"}
          </Button>
        </div>
      </div>
    </div>
  );
}
