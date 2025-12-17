'use client';

import { useState, useEffect } from 'react';
import { initApiClient, createTokenGetter } from '@/lib/api';
import { useUser, useStackApp } from '@stackframe/stack';

interface TemplateField {
  key: string;
  label: string;
  type: 'boolean' | 'number' | 'string' | 'select' | 'range' | 'multi_select';
  required?: boolean;
  description?: string;
  section?: string;
  default?: any;
  min?: number;
  max?: number;
  step?: number;
  options?: Array<{ value: string; label: string }>;
  options_source?: string;
}

interface StrategyConfigFormProps {
  templateId: string;
  templateName: string;
  templateDescription: string;
  fields: TemplateField[];
  initialValues?: Record<string, any>;
  onChange: (config: Record<string, any>) => void;
}

export function StrategyConfigForm({
  templateId,
  templateName,
  templateDescription,
  fields = [],
  initialValues = {},
  onChange,
}: StrategyConfigFormProps) {
  const user = useUser();
  const stackApp = useStackApp();
  const [config, setConfig] = useState<Record<string, any>>(() => {
    const defaults: Record<string, any> = {};
    if (fields && Array.isArray(fields)) {
      fields.forEach((field) => {
        defaults[field.key] = initialValues[field.key] ?? field.default ?? (field.type === 'boolean' ? false : field.type === 'number' ? 0 : '');
      });
    }
    return defaults;
  });

  const [dynamicOptions, setDynamicOptions] = useState<Record<string, Array<{ value: string; label: string }>>>({});

  useEffect(() => {
    onChange(config);
  }, [config, onChange]);

  useEffect(() => {
    const loadDynamicOptions = async () => {
      if (!user || !fields) return;
      
      const fieldsWithOptions = fields.filter(f => f.options_source);
      if (fieldsWithOptions.length === 0) return;

      const api = initApiClient(createTokenGetter(user, stackApp));
      const optionsMap: Record<string, Array<{ value: string; label: string }>> = {};

      for (const field of fieldsWithOptions) {
        if (field.options_source === 'external_data_sources') {
          try {
            const sources = await api.get<any[]>('/external-data-sources?is_active=true');
            optionsMap[field.key] = sources.map(s => ({
              value: s.id,
              label: s.name,
            }));
          } catch (err) {
            console.error(`Error loading options for ${field.key}:`, err);
          }
        }
      }

      setDynamicOptions(optionsMap);
    };

    loadDynamicOptions();
  }, [user, stackApp, fields]);

  const handleChange = (key: string, value: any) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  };

  const fieldsBySection = (fields || []).reduce((acc, field) => {
    const section = field.section || 'General';
    if (!acc[section]) acc[section] = [];
    acc[section].push(field);
    return acc;
  }, {} as Record<string, TemplateField[]>);

  const renderField = (field: TemplateField) => {
    const value = config[field.key];
    const fieldOptions = field.options || dynamicOptions[field.key] || [];

    switch (field.type) {
      case 'boolean':
        return (
          <div key={field.key} className="flex items-start gap-3 py-2">
            <input
              type="checkbox"
              id={field.key}
              checked={value || false}
              onChange={(e) => handleChange(field.key, e.target.checked)}
              className="mt-0.5 w-4 h-4 text-[#2563eb] border-[#e5e7eb] rounded focus:ring-[#2563eb] focus:ring-2"
            />
            <div className="flex-1">
              <label htmlFor={field.key} className="text-sm font-medium text-[#111827] cursor-pointer block">
                {field.label}
                {field.required && <span className="text-[#ef4444] ml-1">*</span>}
              </label>
              {field.description && (
                <p className="text-xs text-[#6b7280] mt-1">{field.description}</p>
              )}
            </div>
          </div>
        );

      case 'number':
        return (
          <div key={field.key} className="space-y-2">
            <label htmlFor={field.key} className="block text-sm font-medium text-[#111827]">
              {field.label}
              {field.required && <span className="text-[#ef4444] ml-1">*</span>}
            </label>
            {field.description && (
              <p className="text-xs text-[#6b7280]">{field.description}</p>
            )}
            <div className="flex items-center gap-3">
              <input
                type="number"
                id={field.key}
                value={value ?? ''}
                onChange={(e) => handleChange(field.key, Number(e.target.value))}
                min={field.min}
                max={field.max}
                step={field.step}
                className="flex-1 px-4 py-3 text-sm text-[#111827] bg-white border border-[#e5e7eb] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb] focus:border-transparent transition-all duration-200"
              />
              {field.min !== undefined && field.max !== undefined && (
                <div className="text-xs text-[#9ca3af] min-w-[80px]">
                  {field.min} - {field.max}
                </div>
              )}
            </div>
          </div>
        );

      case 'select':
        return (
          <div key={field.key} className="space-y-2">
            <label htmlFor={field.key} className="block text-sm font-medium text-[#111827]">
              {field.label}
              {field.required && <span className="text-[#ef4444] ml-1">*</span>}
            </label>
            {field.description && (
              <p className="text-xs text-[#6b7280]">{field.description}</p>
            )}
            <select
              id={field.key}
              value={value || ''}
              onChange={(e) => handleChange(field.key, e.target.value)}
              className="w-full px-4 py-3 text-sm text-[#111827] bg-white border border-[#e5e7eb] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb] focus:border-transparent transition-all duration-200"
            >
              <option value="">Seleccionar...</option>
              {fieldOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        );

      case 'string':
        return (
          <div key={field.key} className="space-y-2">
            <label htmlFor={field.key} className="block text-sm font-medium text-[#111827]">
              {field.label}
              {field.required && <span className="text-[#ef4444] ml-1">*</span>}
            </label>
            {field.description && (
              <p className="text-xs text-[#6b7280]">{field.description}</p>
            )}
            <input
              type="text"
              id={field.key}
              value={value || ''}
              onChange={(e) => handleChange(field.key, e.target.value)}
              className="w-full px-4 py-3 text-sm text-[#111827] bg-white border border-[#e5e7eb] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2563eb] focus:border-transparent transition-all duration-200"
            />
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {Object.entries(fieldsBySection).map(([section, sectionFields]) => (
        <div key={section} className="space-y-4">
          {section !== 'General' && (
            <h4 className="text-xs font-semibold text-[#6b7280] uppercase tracking-wider mb-3">
              {section}
            </h4>
          )}
          <div className="space-y-4">
            {sectionFields.map(renderField)}
          </div>
        </div>
      ))}
    </div>
  );
}
