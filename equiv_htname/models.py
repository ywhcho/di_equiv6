from django.db import models


class MedicinesMedicine(models.Model):
    """
    DB: medicines_medicine
    의약정보 검색 및 wfco 전체 비교에 사용
    """
    wfco = models.CharField('활성성분코드', max_length=20, blank=True, default='')
    htname = models.CharField('약품명', max_length=255, blank=True, default='')
    ee = models.TextField('효능', blank=True, default='')
    ingr_t = models.CharField('성분명', max_length=255, blank=True, default='')
    company = models.CharField('회사', max_length=255, blank=True, default='')
    cfno = models.CharField('효능분류', max_length=20, blank=True, default='')
    atc = models.CharField('ATC분류', max_length=50, blank=True, default='')
    ypri24 = models.CharField('연생산실적', max_length=50, blank=True, default='')

    class Meta:
        db_table = 'medicines_medicine'
        managed = False

    def __str__(self):
        return f"{self.htname} ({self.wfco})"


class MedInteractionMfname(models.Model):
    """
    DB: med_interaction_mfname
    wfco 앞 6자리 비교로 동일성분 찾기에 사용
    """
    wfco = models.CharField('활성성분코드', max_length=20, blank=True, default='')
    ingr_t = models.CharField('성분명', max_length=255, blank=True, default='')
    cfno = models.CharField('효능분류', max_length=20, blank=True, default='')
    atc = models.CharField('ATC분류', max_length=50, blank=True, default='')
    ypri24 = models.CharField('연생산실적', max_length=50, blank=True, default='')

    class Meta:
        db_table = 'med_interaction_mfname'
        managed = False

    def __str__(self):
        return f"{self.wfco} {self.ingr_t}"


class MedicinesDruginfo(models.Model):
    """
    DB: medicines_druginfo
    DI 버튼 클릭 시 의약정보 상세 팝업에 사용
    """
    htname = models.CharField('약품명', max_length=255, blank=True, default='')
    ingr_t = models.CharField('성분명', max_length=500, blank=True, default='')
    sthunite_t = models.CharField('함량', max_length=255, blank=True, default='')
    ypri24 = models.CharField('연생산액', max_length=50, blank=True, default='')
    canc_date = models.CharField('사용종료일', max_length=50, blank=True, default='')
    company = models.CharField('회사명', max_length=255, blank=True, default='')
    kfregcd = models.CharField('품목기준코드', max_length=50, blank=True, default='')
    ee = models.TextField('효능', blank=True, default='')
    ud = models.TextField('용량', blank=True, default='')
    nb = models.TextField('주의사항', blank=True, default='')

    class Meta:
        db_table = 'medicines_druginfo'
        managed = False

    def __str__(self):
        return f"{self.htname}"
