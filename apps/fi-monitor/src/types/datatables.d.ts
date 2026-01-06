/**
 * Type declarations for DataTables.net packages
 * These packages don't include TypeScript definitions
 */

declare module 'datatables.net-react' {
  import { ComponentType, RefObject } from 'react';
  
  interface DataTableProps {
    data?: any[];
    columns?: Array<{
      data?: string | null;
      title?: string;
      render?: (data: any, type: string, row: any) => string;
      className?: string;
      orderable?: boolean;
      searchable?: boolean;
      width?: string;
    }>;
    options?: {
      paging?: boolean;
      searching?: boolean;
      ordering?: boolean;
      info?: boolean;
      pageLength?: number;
      lengthMenu?: number[];
      order?: Array<[number, 'asc' | 'desc']>;
      dom?: string;
      responsive?: boolean;
      scrollX?: boolean;
      scrollY?: string;
      [key: string]: any;
    };
    className?: string;
    ref?: RefObject<HTMLTableElement>;
    children?: React.ReactNode;
  }

  interface DataTableComponent extends ComponentType<DataTableProps> {
    use: (extension: any) => void;
  }

  const DataTable: DataTableComponent;
  export default DataTable;
}

declare module 'datatables.net-dt' {
  const DT: any;
  export default DT;
}

declare module 'datatables.net-dt/css/dataTables.dataTables.min.css' {
  const content: any;
  export default content;
}
