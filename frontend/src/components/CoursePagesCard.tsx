import React from 'react';
import {
  Badge, Card, Icon, IconButton,
} from '@openedx/paragon';
import { AutoAwesome } from '@openedx/paragon/icons';

interface CoursePagesCardProps {
  title: string;
  description: React.ReactNode;
  badge?: string;
  actionLabel?: string;
  onClick: React.MouseEventHandler<HTMLButtonElement>;
}

const CoursePagesCard = ({
  title,
  description,
  badge,
  actionLabel = 'Open AI Extensions Settings',
  onClick,
}: CoursePagesCardProps) => (
  <Card
    className="shadow justify-content-between"
  >
    <Card.Header
      title={title}
      subtitle={
        badge && (
          <Badge variant="info" className="mt-1">
            {badge}
          </Badge>
        )
      }
      actions={(
        <div className="mt-1">
          <IconButton src={AutoAwesome} alt={actionLabel} onClick={onClick} iconAs={Icon} />
        </div>
      )}
      size="sm"
    />
    <Card.Body>
      <Card.Section>
        {description}
      </Card.Section>
    </Card.Body>
  </Card>
);

export default CoursePagesCard;
