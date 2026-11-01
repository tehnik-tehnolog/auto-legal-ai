export interface StreamlitFile {
  name: string;
  path: string;
  language: string;
  content: string;
  description: string;
}

export type TemplateId = 'minimal' | 'starter' | 'data' | 'chat' | 'multipage';

export interface StreamlitTemplate {
  id: TemplateId;
  name: string;
  badge: string;
  summary: string;
  pythonCode: string;
  requirements: string;
  configToml: string;
  secretsToml: string;
  readme: string;
  gitignore: string;
  additionalFiles?: { path: string; content: string; language: string }[];
}

export interface AppSettings {
  theme: 'light' | 'dark';
  wideMode: boolean;
  sidebarExpanded: boolean;
}
