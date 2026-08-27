function board(currentUserId, isSuperuser = false) {
    const csrftoken = document.querySelector('#task-form > input').value;
    const api_client = axios.create({
        baseURL: '/api',
        headers: {'X-CSRFToken': csrftoken},
    });

    return {
        currentUserId: currentUserId,
        isSuperuser: isSuperuser,
        showSettingsPage: false,
        openModal: false,
        taskDetailsModal: false,
        showArchiveModal: false,
        showArchiveColumn: JSON.parse(localStorage.getItem('KB-showArchiveColumn')) || false,
        archiveLimit: 15,
        imagePreviewModal: false,
        previewImageUrl: '',
        isDraggingFile: false,
        isDraggingCommentFile: false,
        activeTaskTab: 'details',

        selectedGroup: null,
        settingsGroup: null,
        _skipGroupWatch: false,
        groups: [],
        users: [],
        settingsGroupMembers: [],
        tasks: [],
        archivedTasks: [],
        notifications: [],
        showNotifications: false,

        availableUsers: [],
        userSearchQuery: "",

        selectedUserFilter: "",
        priorityFilter: "",
        deadlineFrom: "",
        deadlineTo: "",
        createdFrom: "",
        createdTo: "",
        searchText: "",

        selectedTask: null,
        checklistItems: [],
        newChecklistText: "",
        comments: [],
        newCommentText: "",
        commentFile: null,
        taskAttachments: [],
        history: [],

        showMentionDropdown: false,
        mentionFilteredUsers: [],
        mentionQuery: '',

        newTask: {
            name: "",
            description: "",
            deadline: null,
            priority: 2,
            boardName: "todo",
            assigned_to: null,
            co_executors: [],
            files: []
        },

        bannerImage: localStorage.getItem('KB-bannerImage') || "",
        colors: [
            {label: '#3182ce', value: 'blue'},
            {label: '#38a169', value: 'green'},
            {label: '#967bb6', value: 'purple'},
            {label: '#e53e3e', value: 'red'}
        ],
        colorSelected: JSON.parse(localStorage.getItem('KB-theme')) || {label: '#3182ce', value: 'blue'},
        boards: [
            {id: 'todo', title: 'Сделать'},
            {id: 'progress', title: 'В процессе'},
            {id: 'review', title: 'На проверке'},
            {id: 'done', title: 'Выполнено'}
        ],

        get isTaskCreator() {
            return this.selectedTask && (this.selectedTask.created_by_id === this.currentUserId);
        },

        get currentGroupObj() {
            return this.groups.find(g => g.uuid === this.selectedGroup);
        },

        get settingsGroupObj() {
            return this.groups.find(g => g.uuid === this.settingsGroup);
        },

        get canManageSettingsGroup() {
            return Boolean(
                this.settingsGroup &&
                this.groups.some(g => g.uuid === this.settingsGroup)
            );
        },

        get isSettingsGroupOwner() {
            return this.isSuperuser || this.settingsGroupObj?.owner_id === this.currentUserId;
        },

        get filteredAvailableUsers() {
            const query = this.userSearchQuery.trim().toLowerCase();
            if (!query) {
                return this.availableUsers;
            }
            return this.availableUsers.filter(user =>
                user.username.toLowerCase().includes(query)
            );
        },

        get hasActiveFilters() {
            return this.selectedUserFilter !== "" ||
                   this.priorityFilter !== "" ||
                   this.deadlineFrom !== "" ||
                   this.deadlineTo !== "" ||
                   this.createdFrom !== "" ||
                   this.createdTo !== "" ||
                   this.searchText !== "";
        },

        toggleArchiveColumn() {
            this.showArchiveColumn = !this.showArchiveColumn;
            localStorage.setItem('KB-showArchiveColumn', JSON.stringify(this.showArchiveColumn));
        },

        clearFilters() {
            this.selectedUserFilter = "";
            this.priorityFilter = "";
            this.deadlineFrom = "";
            this.deadlineTo = "";
            this.createdFrom = "";
            this.createdTo = "";
            this.searchText = "";
        },

        isDeadlineOverdue(t) {
            if (!t.deadline || t.boardName === 'done') return false;
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            const deadlineDate = new Date(t.deadline);
            deadlineDate.setHours(0, 0, 0, 0);
            return deadlineDate < today;
        },

        closeTopModal() {
            if (this.imagePreviewModal) {
                this.imagePreviewModal = false;
            } else if (this.showMentionDropdown) {
                this.showMentionDropdown = false;
            } else if (this.taskDetailsModal) {
                this.taskDetailsModal = false;
            } else if (this.showArchiveModal) {
                this.showArchiveModal = false;
            } else if (this.showNotifications) {
                this.showNotifications = false;
            } else if (this.openModal) {
                this.openModal = false;
            } else if (this.showSettingsPage) {
                this.showSettingsPage = false;
            }
        },

        closeAllModals() {
            this.openModal = false;
            this.taskDetailsModal = false;
            this.showArchiveModal = false;
            this.imagePreviewModal = false;
            this.showNotifications = false;
            this.showMentionDropdown = false;
        },

        async initBoard() {
            this.$watch('selectedGroup', async (value, oldValue) => {
                if (this._skipGroupWatch || !value || value === oldValue) {
                    return;
                }
                await this.onGroupChange();
            });
            await this.loadGroups();
            setInterval(() => this.loadNotifications(), 15000);
        },

        async loadGroups() {
            const res = await api_client.get('/groups/');
            this.groups = res.data;

            if (this.groups.length > 0) {
                const urlParams = new URLSearchParams(window.location.search);
                const queryBoard = urlParams.get('board') || urlParams.get('group');

                const uuidRegex = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
                const pathMatch = window.location.pathname.match(uuidRegex);
                const pathBoard = pathMatch ? pathMatch[0] : null;

                const targetBoard = queryBoard || pathBoard;

                if (targetBoard && this.groups.some(g => g.uuid === targetBoard)) {
                    this.selectedGroup = targetBoard;
                } else {
                    const savedGroup = localStorage.getItem('KB-selectedGroup');
                    if (savedGroup && this.groups.some(g => g.uuid === savedGroup)) {
                        this.selectedGroup = savedGroup;
                    } else {
                        this.selectedGroup = this.groups[0].uuid;
                    }
                }

                localStorage.setItem('KB-selectedGroup', this.selectedGroup);
            }
        },

        async onGroupChange() {
            if (!this.selectedGroup) {
                return;
            }

            const groupId = this.selectedGroup;
            localStorage.setItem('KB-selectedGroup', groupId);
            this.tasks = [];
            this.archivedTasks = [];
            this.archiveLimit = 15;
            this.selectedUserFilter = "";

            try {
                await Promise.all([
                    this.loadTasks(groupId),
                    this.loadMembers(groupId),
                    this.loadArchivedTasks(groupId),
                ]);
                await this.loadNotifications();
            } catch (e) {
                console.error('Failed to load board data:', e);
                if (this.selectedGroup === groupId) {
                    this.tasks = [];
                    this.archivedTasks = [];
                }
            }
        },

        async openSettings() {
            this.settingsGroup = this.selectedGroup;
            await this.loadAvailableUsers();
            await this.loadSettingsGroupData();
            this.showSettingsPage = true;
        },

        async selectSettingsGroup(group) {
            this.settingsGroup = group.uuid;
            await this.loadSettingsGroupData();
        },

        async loadSettingsGroupData() {
            if (!this.settingsGroup || !this.canManageSettingsGroup) {
                this.settingsGroupMembers = [];
                return;
            }

            await this.loadSettingsGroupMembers();
        },

        async loadSettingsGroupMembers() {
            if (!this.settingsGroup) return;
            const res = await api_client.get(`/groups/${this.settingsGroup}/members/`);
            this.settingsGroupMembers = res.data;
        },

        async loadTasks(groupId = this.selectedGroup) {
            if (!groupId) return;
            const res = await api_client.get(`/boards/${groupId}/tasks/`);
            if (this.selectedGroup === groupId) {
                this.tasks = res.data;
            }
        },

        async loadArchivedTasks(groupId = this.selectedGroup) {
            if (!groupId) return;
            const res = await api_client.get(`/boards/${groupId}/archived-tasks/`);
            if (this.selectedGroup === groupId) {
                this.archivedTasks = res.data;
            }
        },

        async loadMembers(groupId = this.selectedGroup) {
            if (!groupId) return;
            const res = await api_client.get(`/groups/${groupId}/members/`);
            if (this.selectedGroup === groupId) {
                this.users = res.data;
            }
        },

        isGroupMember(userId) {
            return this.settingsGroupMembers.some(u => u.id === userId);
        },

        toggleGroupMember(user) {
            if (!this.isSettingsGroupOwner) return;
            if (this.isGroupMember(user.id)) {
                this.settingsGroupMembers = this.settingsGroupMembers.filter(u => u.id !== user.id);
            } else {
                this.settingsGroupMembers.push(user);
            }
        },

        removeGroupMember(userId) {
            if (!this.isSettingsGroupOwner) return;
            this.settingsGroupMembers = this.settingsGroupMembers.filter(u => u.id !== userId);
        },

        toggleAllAvailableUsers(checked) {
            if (!this.isSettingsGroupOwner) return;
            const users = this.filteredAvailableUsers;
            if (checked) {
                users.forEach(u => {
                    if (!this.isGroupMember(u.id)) {
                        this.settingsGroupMembers.push(u);
                    }
                });
            } else {
                const userIds = users.map(u => u.id);
                this.settingsGroupMembers = this.settingsGroupMembers.filter(
                    u => !userIds.includes(u.id)
                );
            }
        },

        async saveGroupMembers() {
            if (!this.isSettingsGroupOwner) {
                alert("Только создатель группы может изменять состав участников.");
                return;
            }
            try {
                const userIds = this.settingsGroupMembers.map(u => u.id);
                await api_client.post(`/groups/${this.settingsGroup}/members/`, { users: userIds });
                await this.loadSettingsGroupMembers();
                if (this.settingsGroup === this.selectedGroup) {
                    await this.loadMembers();
                }
                alert("Состав участников группы сохранен!");
            } catch(e) {
                alert(e.response?.data?.detail || "Ошибка при сохранении участников");
            }
        },

        async loadAvailableUsers() {
            try {
                const res = await api_client.get('/users/');
                this.availableUsers = res.data;
            } catch (e) {
                console.error(e);
                this.availableUsers = [];
            }
        },

        async saveAllSettings() {
            const theme = JSON.stringify(this.colorSelected);
            localStorage.setItem('KB-theme', theme);
            localStorage.setItem('KB-bannerImage', this.bannerImage);
            if (this.isSettingsGroupOwner) {
                await this.saveGroupMembers();
            }
            this.showSettingsPage = false;
        },

        async loadNotifications() {
            const res = await api_client.get('/notifications/');
            this.notifications = res.data;
        },

        getDoneBoardCount(boardId) {
            const activeCount = this.filteredTasks(boardId).length;
            if (boardId !== 'done') return activeCount;

            const autoArchivedDoneCount = this.archivedTasks.filter(t =>
                t.boardName === 'done' && t.archive_reason && t.archive_reason.includes('Автоматическая')
            ).length;

            return activeCount + autoArchivedDoneCount;
        },

        // ФИЛЬТРАЦИЯ И СОРТИРОВКА ДЛЯ ОСНОВНЫХ КОЛОНОК
        filteredTasks(boardId) {
            const search = this.searchText.trim().toLowerCase();

            let result = this.tasks.filter(t => {
                if (t.boardName !== boardId) return false;
                if (this.selectedUserFilter && t.assigned_to != this.selectedUserFilter) return false;
                if (this.priorityFilter && t.priority != this.priorityFilter) return false;

                if (this.deadlineFrom && (!t.deadline || t.deadline < this.deadlineFrom)) return false;
                if (this.deadlineTo && (!t.deadline || t.deadline > this.deadlineTo)) return false;

                const createdDate = t.date ? t.date.split('T')[0] : '';
                if (this.createdFrom && (!createdDate || createdDate < this.createdFrom)) return false;
                if (this.createdTo && (!createdDate || createdDate > this.createdTo)) return false;

                if (search) {
                    const matchName = t.name && t.name.toLowerCase().includes(search);
                    const matchDesc = t.description && t.description.toLowerCase().includes(search);
                    const matchId = t.formatted_id && String(t.formatted_id).toLowerCase().includes(search);
                    if (!matchName && !matchDesc && !matchId) return false;
                }
                return true;
            });

            // ДЛЯ КОЛОНКИ "ВЫПОЛНЕНО": Строгая сортировка ИСКЛЮЧИТЕЛЬНО по дате выполнения (новые сверху)
            if (boardId === 'done') {
                result.sort((a, b) => {
                    const getTime = (t) => {
                        if (t.completed_at) return new Date(t.completed_at).getTime();
                        if (t.updated) return new Date(t.updated).getTime();
                        if (t.date) return new Date(t.date).getTime();
                        return 0;
                    };
                    return getTime(b) - getTime(a);
                });
            }

            return result;
        },

        filteredArchivedTasks() {
            const search = this.searchText.trim().toLowerCase();

            return this.archivedTasks.filter(t => {
                if (this.selectedUserFilter && t.assigned_to != this.selectedUserFilter) return false;
                if (this.priorityFilter && t.priority != this.priorityFilter) return false;

                if (this.deadlineFrom && (!t.deadline || t.deadline < this.deadlineFrom)) return false;
                if (this.deadlineTo && (!t.deadline || t.deadline > this.deadlineTo)) return false;

                const createdDate = t.date ? t.date.split('T')[0] : '';
                if (this.createdFrom && (!createdDate || createdDate < this.createdFrom)) return false;
                if (this.createdTo && (!createdDate || createdDate > this.createdTo)) return false;

                if (search) {
                    const matchName = t.name && t.name.toLowerCase().includes(search);
                    const matchDesc = t.description && t.description.toLowerCase().includes(search);
                    const matchId = t.formatted_id && String(t.formatted_id).toLowerCase().includes(search);
                    if (!matchName && !matchDesc && !matchId) return false;
                }
                return true;
            });
        },

        get visibleArchivedTasks() {
            return this.filteredArchivedTasks().slice(0, this.archiveLimit);
        },

        loadMoreArchived() {
            this.archiveLimit += 15;
        },

        getPriorityBadgeClass(p) {
            if (p == 4) return 'bg-red-600';
            if (p == 3) return 'bg-orange-500';
            if (p == 2) return 'bg-yellow-500';
            return 'bg-green-600';
        },

        getCardDeadlineClass(t) {
            if (!t.deadline || t.boardName === 'done') return 'bg-white text-gray-800';

            const today = new Date();
            today.setHours(0, 0, 0, 0);

            const deadlineDate = new Date(t.deadline);
            deadlineDate.setHours(0, 0, 0, 0);

            const diffTime = deadlineDate - today;
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

            if (diffDays <= 3) {
                return 'bg-red-100 text-red-950 shadow-sm';
            } else if (diffDays <= 7) {
                return 'bg-yellow-100 text-yellow-950 shadow-sm';
            } else {
                return 'bg-green-100 text-green-950 shadow-sm';
            }
        },

        getPriorityBorderStyle(p) {
            if (p == 4) return 'border-left: 5px solid #ef4444 !important;';
            if (p == 3) return 'border-left: 5px solid #f97316 !important;';
            if (p == 2) return 'border-left: 5px solid #eab308 !important;';
            return 'border-left: 5px solid #22c55e !important;';
        },

        async openTask(task) {
            this.selectedTask = {...task};
            this.activeTaskTab = 'details';

            const [cRes, hRes, aRes, clRes] = await Promise.all([
                api_client.get(`/task/${task.uuid}/comments/`),
                api_client.get(`/task/${task.uuid}/history/`),
                api_client.get(`/task/${task.uuid}/attachments/`),
                api_client.get(`/task/${task.uuid}/checklist/`)
            ]);

            this.comments = cRes.data;
            this.history = hRes.data;
            this.taskAttachments = aRes.data;
            this.checklistItems = clRes.data;
            this.taskDetailsModal = true;
        },

        async toggleFollow() {
            if (!this.selectedTask) return;
            const res = await api_client.post(`/task/${this.selectedTask.uuid}/toggle-follow/`);
            this.selectedTask.is_following = res.data.is_following;
            this.selectedTask.followers_count = res.data.followers_count;
            await this.loadTasks();
        },

        async saveTask() {
            try {
                const payload = this.isTaskCreator
                    ? this.selectedTask
                    : { assigned_to: this.selectedTask.assigned_to || null };
                await api_client.patch(`/task/${this.selectedTask.uuid}/`, payload);
                await this.loadTasks();
                await this.loadArchivedTasks();
                this.taskDetailsModal = false;
            } catch (e) {
                alert(e.response?.data?.detail || "Ошибка при сохранении");
            }
        },

        async addChecklistItem() {
            if (!this.newChecklistText.trim()) return;
            const res = await api_client.post(`/task/${this.selectedTask.uuid}/checklist/`, { text: this.newChecklistText });
            this.checklistItems.push(res.data);
            this.newChecklistText = "";
            await this.loadTasks();
        },

        async toggleChecklistItem(item) {
            item.is_completed = !item.is_completed;
            await api_client.patch(`/checklist/${item.id}/`, { is_completed: item.is_completed });
            await this.loadTasks();
        },

        async deleteChecklistItem(id) {
            await api_client.delete(`/checklist/${id}/`);
            this.checklistItems = this.checklistItems.filter(i => i.id !== id);
            await this.loadTasks();
        },

        onCommentInput(e) {
            const val = this.newCommentText;
            const lastAtIndex = val.lastIndexOf('@');

            if (lastAtIndex !== -1) {
                const query = val.substring(lastAtIndex + 1);
                if (!query.includes(' ')) {
                    this.mentionQuery = query.toLowerCase();
                    this.mentionFilteredUsers = this.users.filter(u =>
                        u.username.toLowerCase().includes(this.mentionQuery)
                    );
                    this.showMentionDropdown = this.mentionFilteredUsers.length > 0;
                    return;
                }
            }
            this.showMentionDropdown = false;
        },

        insertMention(username) {
            const val = this.newCommentText;
            const lastAtIndex = val.lastIndexOf('@');
            if (lastAtIndex !== -1) {
                this.newCommentText = val.substring(0, lastAtIndex) + '@' + username + ' ';
            }
            this.showMentionDropdown = false;
        },

        handlePaste(e, target) {
            const items = (e.clipboardData || e.originalEvent?.clipboardData)?.items;
            if (!items) return;

            for (let i = 0; i < items.length; i++) {
                if (items[i].type.indexOf("image") === 0) {
                    const blob = items[i].getAsFile();
                    const file = new File([blob], `screenshot_${Date.now()}.png`, { type: blob.type });

                    if (target === 'comment') {
                        this.commentFile = file;
                    } else if (target === 'task') {
                        if (this.selectedTask) {
                            this.uploadTaskFileDirect(file);
                        }
                    } else if (target === 'newTask') {
                        this.newTask.files = [...(this.newTask.files || []), file];
                    }
                }
            }
        },

        handleCommentFileDrop(e) {
            this.isDraggingCommentFile = false;
            const file = e.dataTransfer.files[0];
            if (file) {
                this.commentFile = file;
            }
        },

        async addComment() {
            if (!this.newCommentText.trim() && !this.commentFile) return;

            const res = await api_client.post(`/task/${this.selectedTask.uuid}/comments/`, {
                text: this.newCommentText.trim()
            });

            if (this.commentFile) {
                const formData = new FormData();
                formData.append("file", this.commentFile);
                await api_client.post(`/comment/${res.data.id}/attachments/`, formData);
                this.commentFile = null;
            }

            const updatedCommentRes = await api_client.get(`/task/${this.selectedTask.uuid}/comments/`);
            this.comments = updatedCommentRes.data;
            this.newCommentText = "";
            this.showMentionDropdown = false;
        },

        async deleteComment(id) {
            if (!confirm("Удалить комментарий?")) return;
            await api_client.delete(`/comment/${id}/`);
            this.comments = this.comments.filter(c => c.id !== id);
        },

        isImageFile(filename) {
            if (!filename) return false;
            return /\.(jpg|jpeg|png|gif|webp)$/i.test(filename);
        },

        openImagePreview(url) {
            this.previewImageUrl = url;
            this.imagePreviewModal = true;
        },

        async handleTaskFileDrop(e) {
            this.isDraggingFile = false;
            const file = e.dataTransfer.files[0];
            if (file) await this.uploadTaskFileDirect(file);
        },

        async uploadTaskFileDirect(file) {
            const formData = new FormData();
            formData.append('file', file);
            const res = await api_client.post(`/task/${this.selectedTask.uuid}/attachments/`, formData);
            this.taskAttachments.push(res.data);
        },

        async deleteTaskAttachment(id) {
            await api_client.delete(`/task/attachments/${id}/`);
            this.taskAttachments = this.taskAttachments.filter(a => a.id !== id);
        },

        async archiveOrRemoveTask(task) {
            if (!confirm("Отправить задачу в архив?")) return;
            await api_client.delete(`/task/${task.uuid}/`);
            await this.loadTasks();
            await this.loadArchivedTasks();
        },

        async restoreTask(uuid) {
            await api_client.post(`/task/${uuid}/restore/`);
            await this.loadTasks();
            await this.loadArchivedTasks();
        },

        async openArchiveModal() {
            await this.loadArchivedTasks();
            this.showArchiveModal = true;
        },

        onDragStart(e, uuid) { e.dataTransfer.setData('text/plain', uuid); },
        onDragOver(e) { e.preventDefault(); },
        onDragEnter(e) {},
        onDragLeave(e) {},

        async onDrop(e, targetBoardId) {
            e.preventDefault();
            const uuid = e.dataTransfer.getData('text/plain');

            if (targetBoardId === 'archive') {
                const taskToArchive = this.tasks.find(t => t.uuid === uuid);
                if (taskToArchive) {
                    await this.archiveOrRemoveTask(taskToArchive);
                }
                return;
            }

            const task = this.tasks.find(t => t.uuid === uuid);

            if (task && task.boardName !== targetBoardId) {
                try {
                    await api_client.patch(`/task/${uuid}/`, { boardName: targetBoardId });
                    await this.loadTasks();
                    await this.loadArchivedTasks(); // Обновляем данные архива!
                } catch (err) {
                    alert(err.response?.data?.detail || "У вас нет прав для перемещения этой задачи в данный статус.");
                }
            }
        },

        showModal(board) {
            this.newTask.boardName = board.id;
            this.openModal = true;
        },

        async addTask() {
            try {
                const res = await api_client.post(`/boards/${this.selectedGroup}/tasks/`, this.newTask);
                const createdTaskUuid = res.data.uuid;

                if (this.newTask.files && this.newTask.files.length > 0) {
                    for (let i = 0; i < this.newTask.files.length; i++) {
                        const formData = new FormData();
                        formData.append('file', this.newTask.files[i]);
                        await api_client.post(`/task/${createdTaskUuid}/attachments/`, formData);
                    }
                }

                this.openModal = false;
                this.newTask = {
                    name: "",
                    description: "",
                    deadline: null,
                    priority: 2,
                    boardName: "todo",
                    assigned_to: null,
                    co_executors: [],
                    files: []
                };
                await this.loadTasks();
            } catch (e) {
                alert(e.response?.data?.detail || "Ошибка при создании задачи");
            }
        },

        formatDate(dateStr) {
            if (!dateStr) return '';
            return new Date(dateStr).toLocaleString("ru-RU", {
                day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit"
            });
        },

        formatShortDate(dateStr) {
            if (!dateStr) return '';
            return new Date(dateStr).toLocaleDateString("ru-RU", {
                day: "2-digit", month: "2-digit"
            });
        },

        async readAllNotifications() {
            await api_client.post("/notifications/read-all/");
            this.notifications.forEach(n => n.is_read = true);
        },

        async markNotificationAsRead(id) {
            await api_client.patch(`/notifications/${id}/`, { is_read: true });
            const n = this.notifications.find(x => x.id === id);
            if (n) n.is_read = true;
        },

        async openNotification(item) {
            await this.markNotificationAsRead(item.id);
            if (item.group_uuid && item.group_uuid !== this.selectedGroup) {
                this._skipGroupWatch = true;
                this.selectedGroup = item.group_uuid;
                this._skipGroupWatch = false;
                await this.onGroupChange();
            }
            const task = this.tasks.find(t => t.uuid === item.task_uuid);
            if (task) {
                await this.openTask(task);
            } else {
                try {
                    const res = await api_client.get(`/task/${item.task_uuid}/`);
                    if (res.data) await this.openTask(res.data);
                } catch(e) {
                    alert("Задача не найдена или была удалена");
                }
            }
            this.showNotifications = false;
        },

        async openTaskByUuid(uuid) {
            const task = this.tasks.find(t => t.uuid === uuid);
            if (task) await this.openTask(task);
            this.showNotifications = false;
        }
    };
}