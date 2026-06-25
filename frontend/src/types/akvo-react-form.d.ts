declare module "akvo-react-form" {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  export const Webform: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const content: any;
  export default content;
}

declare module "akvo-react-form-editor" {
  import { ComponentType } from "react";
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const WebformEditor: ComponentType<any>;
  export default WebformEditor;
}
