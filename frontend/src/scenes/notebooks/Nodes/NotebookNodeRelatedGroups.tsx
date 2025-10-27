import { useValues } from 'kea'

import { RelatedGroups, RelatedGroupsProps } from 'scenes/groups/RelatedGroups'

import { NotebookNodeProps, NotebookNodeType } from '../types'
import { createPostHogWidgetNode } from './NodeWrapper'
import { notebookNodeLogic } from './notebookNodeLogic'

const Component = ({ attributes }: NotebookNodeProps<NotebookNodeRelatedGroupsAttributes>): JSX.Element | null => {
    const { id, groupTypeIndex, type } = attributes
    const { expanded } = useValues(notebookNodeLogic)

    if (!expanded) {
        return null
    }

    return <RelatedGroups groupTypeIndex={groupTypeIndex} id={id} type={type} embedded pageSize={10} />
}

type NotebookNodeRelatedGroupsAttributes = Pick<RelatedGroupsProps, 'id' | 'groupTypeIndex' | 'type'>

export const NotebookNodeRelatedGroups = createPostHogWidgetNode<NotebookNodeRelatedGroupsAttributes>({
    nodeType: NotebookNodeType.RelatedGroups,
    titlePlaceholder: 'Related groups',
    Component,
    resizeable: false,
    expandable: true,
    startExpanded: true,
    attributes: {
        id: {},
        groupTypeIndex: {},
        type: {},
    },
})
