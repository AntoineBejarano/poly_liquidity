'use client';

import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface Tag {
  tag_id: string;
  name: string;
}

interface TagFilterProps {
  tags: Tag[];
  selectedTags: string[];
  onSelectionChange: (selectedTags: string[]) => void;
}

export function TagFilter({ tags, selectedTags, onSelectionChange }: TagFilterProps) {
  const handleTagToggle = (tagId: string) => {
    if (selectedTags.includes(tagId)) {
      onSelectionChange(selectedTags.filter((id) => id !== tagId));
    } else {
      onSelectionChange([...selectedTags, tagId]);
    }
  };

  if (tags.length === 0) {
    return null;
  }

  return (
    <Card className="p-3 border-border">
      <div className="space-y-2">
        <Label className="text-xs font-medium text-foreground">Filtrar por Tags</Label>
        <div className="flex flex-wrap gap-2">
          {tags.map((tag) => {
            const isSelected = selectedTags.includes(tag.tag_id);
            return (
              <div key={tag.tag_id} className="flex items-center space-x-2">
                <Checkbox
                  id={`tag-${tag.tag_id}`}
                  checked={isSelected}
                  onCheckedChange={() => handleTagToggle(tag.tag_id)}
                />
                <Label
                  htmlFor={`tag-${tag.tag_id}`}
                  className="text-xs cursor-pointer flex items-center gap-1"
                >
                  <Badge variant={isSelected ? 'default' : 'outline'} className="text-xs">
                    {tag.name}
                  </Badge>
                </Label>
              </div>
            );
          })}
        </div>
        {selectedTags.length > 0 && (
          <button
            onClick={() => onSelectionChange([])}
            className="text-xs text-muted-foreground hover:text-foreground mt-2"
          >
            Limpiar filtros
          </button>
        )}
      </div>
    </Card>
  );
}

