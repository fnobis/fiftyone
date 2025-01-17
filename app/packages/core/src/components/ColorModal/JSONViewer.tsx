import { useTheme } from "@fiftyone/components";
import { isValidColor } from "@fiftyone/looker/src/overlays/util";
import * as fos from "@fiftyone/state";
import Editor from "@monaco-editor/react";
import React, { useEffect, useRef, useState } from "react";
import { useRecoilValue } from "recoil";
import { COLOR_SCHEME } from "../../utils/links";
import { ActionOption } from "../Actions/Common";
import { Button } from "../utils";
import { SectionWrapper } from "./ShareStyledDiv";
import { validateJSONSetting } from "./utils";

const JSONViewer: React.FC = ({}) => {
  const themeMode = useRecoilValue(fos.theme);
  const theme = useTheme();
  const editorRef = useRef(null);
  const setting = useRecoilValue(fos.sessionColorScheme);
  const { setColorScheme } = fos.useSessionColorScheme();
  const [data, setData] = useState(setting);

  const handleEditorDidMount = (editor) => (editorRef.current = editor);
  const handleEditorChange = (value: string | undefined) => {
    value && setData(JSON.parse(value));
  };

  const onApply = () => {
    if (
      typeof data !== "object" ||
      !data?.colorPool ||
      !Array.isArray(data?.colorPool) ||
      !data?.customizedColorSettings ||
      !Array.isArray(data?.customizedColorSettings) ||
      !data?.customizedColorSettings
    )
      return;
    const { colorPool, customizedColorSettings } = data;
    const validColors = colorPool?.filter((c) => isValidColor(c));
    const validatedSetting = validateJSONSetting(customizedColorSettings);
    setData({
      colorPool: validColors,
      customizedColorSettings: validatedSetting,
    });
    setColorScheme(validColors, validatedSetting, false);
  };

  useEffect(() => {
    setData(setting);
  }, [setting]);

  const haveChanges = JSON.stringify(setting) !== JSON.stringify(data);

  return (
    <div style={{ width: "100%", height: "100%", overflow: "hidden" }}>
      <SectionWrapper>
        You can use the JSON editor to customize the color settings.
        <ActionOption
          href={COLOR_SCHEME}
          text={"Read more"}
          title={"How to set customized color schema?"}
          style={{
            background: "unset",
            color: theme.text.primary,
            paddingTop: 0,
            paddingBottom: 0,
          }}
          svgStyles={{ height: "1rem", marginTop: 7.5 }}
        />
        {haveChanges && (
          <Button
            onClick={onApply}
            style={{ margin: "0.25rem" }}
            text="Save Changes"
            title="Validate color scheme JSON and apply to session color scheme setting"
          />
        )}
      </SectionWrapper>
      <Editor
        defaultLanguage="json"
        theme={themeMode == "dark" ? "vs-dark" : "vs-light"}
        value={JSON.stringify(data, null, 4)}
        width={"100%"}
        height={"calc(100% - 110px)"}
        wrapperProps={{ padding: 0 }}
        onMount={handleEditorDidMount}
        onChange={handleEditorChange}
      />
    </div>
  );
};

export default JSONViewer;
