export type Source={ref_id:number;chunk_id:string;source:string;page:number|null;title:string;excerpt:string};
export type Message={role:'user'|'assistant';content:string;sources?:Source[]};
export type Document={id:string;source:string;chunk_count:number};
