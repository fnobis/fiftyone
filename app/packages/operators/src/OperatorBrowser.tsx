import { createPortal } from "react-dom";
import styled from "styled-components";
import { useOperatorBrowser } from "./state";
import { scrollbarStyles } from "@fiftyone/utilities";
import { Link } from "@mui/material";
import { Close, Help, Lock, Extension } from "@mui/icons-material";
import { useTheme } from "@fiftyone/components";
import { initializationErrors } from "./operators";

// todo: use plugin component
import ErrorView from "../../core/src/plugins/SchemaIO/components/ErrorView";
import BaseStylesProvider from "./BaseStylesProvider";

const BrowserContainer = styled.form`
  position: absolute;
  top: 5rem;
  left: 0;
  max-height: 80vh;
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  z-index: 99999;
`;

const BrowserModal = styled.div`
  align-self: stretch;
  background: ${({ theme }) => theme.background.level2};
  width: 50%;
  padding: 1rem;
`;

const ResultsContainer = styled.div`
  margin-top: 1rem;
  max-height: calc(100% - 64px);
  overflow: auto;
  ${scrollbarStyles}
`;

const QueryInput = styled.input`
  width: 100%;
  background: none;
  outline: none;
  border: none;
  padding: 0.5rem 1rem;
`;
const ChoiceContainer = styled.div`
  display: flex;
  height: 2.5rem;
  line-height: 2.5rem;
  padding: 0 1rem;
  :hover {
    background: ${({ theme }) => theme.background.level1};
    cursor: pointer;
  }
  opacity: ${({ disabled, theme }) => (disabled ? 0.5 : 1)};
  background: ${({ selected, theme }) => selected && theme.primary.plainColor};
`;

const ChoiceDescription = styled.div`
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 60%;
`;

const ChoiceLabel = styled.div`
  margin-left: auto;
  max-width: 38%;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
`;

const ChoiceIcon = styled.div`
  margin-right: 0.5rem;
  line-height: 45px;
`;

const Choice = ({ onClick, choice, selected }) => {
  const disabled = choice.canExecute === false;
  return (
    <ChoiceContainer disabled={disabled} onClick={onClick} selected={selected}>
      <ChoiceIcon>{disabled ? <Lock /> : <Extension />}</ChoiceIcon>
      <ChoiceDescription>{choice.label}</ChoiceDescription>
      {choice.label && <ChoiceLabel>{choice.name}</ChoiceLabel>}
    </ChoiceContainer>
  );
};

const QueryDiv = styled.div`
  position: relative;
  display: flex;
  overflow-x: scroll;
  scrollbar-width: none;
  min-width: 200px;
  flex: 1;

  &::-webkit-scrollbar {
    width: 0px;
    background: transparent;
    display: none;
  }
  &::-webkit-scrollbar-thumb {
    width: 0px;
    display: none;
  }
`;

const IconsContainer = styled.div`
  display: flex;
  margin-left: auto;
  align-items: center;
  z-index: 1;
  column-gap: 0.5rem;
  padding: 0 0.5rem;
  z-index: 801;
`;
const TopBarDiv = styled.div`
  display: flex;
  background-color: ${({ theme }) => theme.background.level1};
  border-radius: 3px;
  border: 1px solid ${({ theme }) => theme.primary.plainBorder};
  box-sizing: border-box;
  height: 52px;
  width: 100%;
`;

export default function OperatorBrowser() {
  const theme = useTheme();
  const browser = useOperatorBrowser();

  if (!browser.isVisible) {
    return null;
  }
  return createPortal(
    <BaseStylesProvider>
      <BrowserContainer
        onSubmit={browser.onSubmit}
        onKeyDown={browser.onKeyDown}
      >
        <BrowserModal>
          <TopBarDiv>
            <QueryDiv>
              <QueryInput
                autoFocus
                placeholder="Search operations by name..."
                onChange={(e) => browser.onChangeQuery(e.target.value)}
              />
            </QueryDiv>
            <IconsContainer>
              {browser.hasQuery && (
                <Close
                  onClick={() => browser.clear()}
                  style={{
                    cursor: "pointer",
                    color: theme.text.secondary,
                  }}
                />
              )}
              <ErrorView
                schema={{
                  view: { detailed: true, popout: true, left: true },
                }}
                data={initializationErrors}
              />
              <Link
                href="https://docs.voxel51.com/user_guide/app.html#operations"
                style={{ display: "flex" }}
                target="_blank"
              >
                <Help style={{ color: theme.text.secondary }} />
              </Link>
            </IconsContainer>
          </TopBarDiv>
          <ResultsContainer>
            {browser.choices.map((choice) => (
              <Choice
                onClick={() => browser.setSelectedAndSubmit(choice)}
                key={choice.value}
                choice={choice}
                selected={choice.value === browser.selectedValue}
              />
            ))}
          </ResultsContainer>
        </BrowserModal>
      </BrowserContainer>
    </BaseStylesProvider>,
    document.body
  );
}
