import { PillButton } from "@fiftyone/components";
import { useOperatorPlacements, usePromptOperatorInput } from "./state";
import { Placement, Places } from "./types";
import { Link } from "@fiftyone/components";
import styled from "styled-components";
import { types } from ".";
import { Operator } from "./operators";
import { withSuspense } from "@fiftyone/state";

function OperatorPlacements(props: OperatorPlacementsProps) {
  const { place } = props;
  const { placements } = useOperatorPlacements(place);

  return placements.map((placement) => (
    <OperatorPlacement
      key={placement?.operator?.uri}
      {...placement}
      place={place}
    />
  ));
}

export default withSuspense(OperatorPlacements, () => null);

const componentByView = {
  Button: ButtonPlacement,
};

function getPlacementComponent(placement: Placement) {
  const viewName = placement?.view?.name;

  return componentByView[viewName] || componentByView.Button;
}

function OperatorPlacement(props: OperatorPlacementProps) {
  const { placement } = props;
  const Component = getPlacementComponent(placement);
  return <Component {...props} />;
}

function ButtonPlacement(props: OperatorPlacementProps) {
  const promptForInput = usePromptOperatorInput();
  const { operator, placement, place } = props;
  const { uri } = operator;
  const { view = {} } = placement;
  const { label } = view;
  const { icon } = view?.options || {};

  const IconComponent = icon && (
    <img src={`/plugins/${icon}`} width={21} height={21} />
  );

  const handleClick = () => {
    promptForInput(uri);
  };

  if (
    place === types.Places.SAMPLES_GRID_ACTIONS ||
    place === types.Places.SAMPLES_GRID_SECONDARY_ACTIONS ||
    place === types.Places.SAMPLES_VIEWER_ACTIONS
  ) {
    return (
      <PillButton
        onClick={handleClick}
        icon={IconComponent}
        text={!icon && label}
        title={label}
        highlight={place === types.Places.SAMPLES_GRID_ACTIONS}
      />
    );
  }

  return (
    <SquareButton to={handleClick} title={label}>
      {IconComponent || label}
    </SquareButton>
  );
}

type OperatorPlacementsProps = {
  place: Places;
};

type OperatorPlacementProps = {
  placement: Placement;
  place: Places;
  operator: Operator;
};

// todo: consolidate and move to component
const SquareButton = styled(Link)`
  display: flex;
  color: var(--fo-palette-primary-plainColor);
  align-items: center;
  cursor: pointer;
  border-bottom: 1px var(--fo-palette-primary-plainColor) solid;
  background: var(--fo-palette-neutral-softBg);
  border-top-left-radius: 3px;
  border-top-right-radius: 3px;
  padding: 9px 3.5px;
`;
