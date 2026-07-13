from django.db import models


class MedInteractionMfname(models.Model):
    """
    DB: med_interaction_mfname
    wfco: 활성성분코드, ingr_t: 영문성분명, kingr_t: 한글성분명, cfno: 효능분류번호, ATC: ATC분류
    """
    wfco = models.CharField('활성성분코드', max_length=20, blank=True, default='')
    igrno1 = models.CharField(max_length=20, blank=True, default='')
    igrno2 = models.CharField(max_length=20, blank=True, default='')
    igrno3 = models.CharField(max_length=20, blank=True, default='')
    igrno4 = models.CharField(max_length=20, blank=True, default='')
    ingr_t = models.CharField('영문성분명', max_length=255, blank=True, default='')  ##ingrnd_t
    kingr_t = models.CharField('한글성분명', max_length=255, blank=True, default='')  ##kingrnd_t
    sthunite_t = models.CharField('함량', max_length=255, blank=True, default='')
    ypri24 = models.CharField('연생산액', max_length=50, blank=True, default='')
    cfno = models.CharField('효능분류번호', max_length=20, blank=True, default='')
    ATC = models.CharField('ATC분류', max_length=50, blank=True, default='')

    class Meta:
        db_table = 'med_interaction_mfname'
        managed = False

    def __str__(self):
        return f"{self.wfco} {self.kingr_t}"


class MedicinesMedicine(models.Model):
    """
    DB: medicines_medicine
    wfco: 활성성분코드, htname: 제품명, ingred: 성분, company: 회사
    cfno: 효능분류, deriv2: 성분계열, ypri24: 연생산실적, ATC: ATC분류
    """
    wfco = models.CharField('활성성분코드', max_length=20, blank=True, default='')
    htname = models.CharField('제품명', max_length=255, blank=True, default='')
    ingr_t = models.CharField('성분', max_length=255, blank=True, default='') #ingred
    company = models.CharField('회사', max_length=255, blank=True, default='')
    cfno = models.CharField('효능분류', max_length=20, blank=True, default='')
    deriv2 = models.CharField('성분계열', max_length=100, blank=True, default='')
    ypri24 = models.CharField('연생산실적', max_length=50, blank=True, default='')
    ATC = models.CharField('ATC분류', max_length=50, blank=True, default='')

    class Meta:
        db_table = 'medicines_medicine'
        managed = False

    def __str__(self):
        return f"{self.htname} ({self.wfco})"


class MedicinesDruginfo(models.Model):
    """
    DB: medicines_druginfo
    DI 버튼 클릭 시 의약정보 상세 팝업에 사용
    """
    htname = models.CharField('약품명', max_length=255, blank=True, default='')
    ingr_t = models.CharField('성분명', max_length=500, blank=True, default='')
    sthunite_t = models.CharField('함량', max_length=255, blank=True, default='')
    ypri24 = models.CharField('연생산액', max_length=50, blank=True, default='')
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
